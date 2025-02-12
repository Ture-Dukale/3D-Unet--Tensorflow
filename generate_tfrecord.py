import os
import sys
import tensorflow as tf
import h5py
import numpy as np
#from configure import conf


"""Generate TFRecord Files.
"""

class GenerateTfRecord (object):
	################################################################################
	# Basic Functions
	################################################################################
	def _float_feature(value):
		return tf.train.Feature(float_list=tf.train.FloatList(value=value))


	def _bytes_feature(value):
		return tf.train.Feature(bytes_list=tf.train.BytesList(value=value))


	def _int64_feature(value):
		return tf.train.Feature(int64_list=tf.train.Int64List(value=value))


	def cut_edge(data):
		'''Cuts zero edge for a 3D image.

		Args:
			data: A 3D image, [Depth, Height, Width, 1].

		Returns:
			original_shape: [Depth, Height, Width]
			cut_size: A list of six integers [Depth_s, Depth_e, Height_s, Height_e, Width_s, Width_e]
		'''

		D, H, W, _ = data.shape
		D_s, D_e = 0, D-1
		H_s, H_e = 0, H-1
		W_s, W_e = 0, W-1

		while D_s < D:
			if data[D_s].sum() != 0:
				break
			D_s += 1
		while D_e > D_s:
			if data[D_e].sum() != 0:
				break
			D_e -= 1
		while H_s < H:
			if data[:,H_s].sum() != 0:
				break
			H_s += 1
		while H_e > H_s:
			if data[:,H_e].sum() != 0:
				break
			H_e -= 1
		while W_s < W:
			if data[:,:,W_s].sum() != 0:
				break
			W_s += 1
		while W_e > W_s:
			if data[:,:,W_e].sum() != 0:
				break
			W_e -= 1

		original_shape = [D, H, W]
		cut_size = [int(D_s), int(D_e+1), int(H_s), int(H_e+1), int(W_s), int(W_e+1)]
		return (original_shape, cut_size)

	def convert_labels(labels):
		'''Converts 0:background / 10:CSF / 150:GM / 250:WM to 0/1/2/3. SLOW!
		'''

		D, H, W, C = labels.shape # these are masks without BG
		output_labels = np.zeros((H, W, 1))

		for d in range(D):
			for h in range(H):
				for w in range(W):
					if labels[d,h,w,0] == 1:
						output_labels[h,w,0] = d + 1
		return output_labels


	def load_subject(raw_data_dir, subject_id):
		#def load_subject(subject_id):	
		'''Load subject data.

		Args:
			subject_id: [1-23]

		Returns:
			[T1, T2, label]
		'''

		# on the kaggle NB collect all the 65 images togather and write as .h5.
		# so that here we will only use the link to load it with its labels.

		image_subject_var = 'image_train_{}'.format(subject_id)
		mask_subject_var = 'mask_train_{}'.format(subject_id)
		#g = h5py.File('/kaggle/input/ink-train-orig-size/train.h5', 'r')
		g = h5py.File(raw_data_dir, 'r')
		input_img = g[image_subject_var][()]
		input_mask = g[mask_subject_var][()]
		g.close()
		input_img = np.expand_dims(input_img, axis=-1)
		input_mask = np.expand_dims(input_mask, axis=-1)
		return [input_img, input_mask]


	def prepare_validation(cutted_image, patch_size, overlap_stepsize):
		"""Determine patches for validation."""

		patch_ids = []

		D, H, W, _ = cutted_image.shape

		drange = list(range(0, D-patch_size+1, overlap_stepsize))
		hrange = list(range(0, H-patch_size+1, overlap_stepsize))
		wrange = list(range(0, W-patch_size+1, overlap_stepsize))

		if (D-patch_size) % overlap_stepsize != 0:
			drange.append(D-patch_size)
		if (H-patch_size) % overlap_stepsize != 0:
			hrange.append(H-patch_size)
		if (W-patch_size) % overlap_stepsize != 0:
			wrange.append(W-patch_size)

		for d in drange:
			for h in hrange:
				for w in wrange:
					patch_ids.append((d, h, w))

		return patch_ids

	################################################################################
	# TFRecord Generation Functions
	################################################################################

	def write_training_examples(T1, label, original_shape, cut_size, output_file):
		"""Create a training tfrecord file.

		Args:
			T1: T1 image. [Depth, Height, Width, 1].
			T2: T2 image. [Depth, Height, Width, 1].
			label: Label. [Depth, Height, Width, 1].
			original_shape: A list of three integers [D, H, W].
			cut_size: A list of six integers [Depth_s, Depth_e, Height_s, Height_e, Width_s, Width_e].
			output_file: The file name for the tfrecord file.
		"""
		writer = tf.io.TFRecordWriter(output_file)

		example = tf.train.Example(features=tf.train.Features(
			feature={
				'image': GenerateTfRecord._bytes_feature([T1[:,:,:,0].tostring()]), #int16
				#'T2': GenerateTfRecord._bytes_feature([T2[:,:,:,0].tostring()]), #int16
				'label': GenerateTfRecord._bytes_feature([label[:,:,:,0].tostring()]), #uint8
				'original_shape': GenerateTfRecord._int64_feature(original_shape),
				'cut_size': GenerateTfRecord._int64_feature(cut_size)
			}
		))

		writer.write(example.SerializeToString())

		writer.close()


	def write_validation_examples(T1, label, patch_size, cut_size, overlap_stepsize, output_file):
		"""Create a validation tfrecord file.

		Args:
			T1: T1 image. [Depth, Height, Width, 1].
			T2: T2 image. [Depth, Height, Width, 1].
			label: Label. [Depth, Height, Width, 1].
			patch_size: An integer.
			cut_size: A list of six integers [Depth_s, Depth_e, Height_s, Height_e, Width_s, Width_e].
			overlap_stepsize: An integer.
			output_file: The file name for the tfrecord file.
		"""

		T1 = T1[cut_size[0]:cut_size[1], cut_size[2]:cut_size[3], cut_size[4]:cut_size[5], :]
		#T2 = T2[cut_size[0]:cut_size[1], cut_size[2]:cut_size[3], cut_size[4]:cut_size[5], :]
		label = label[cut_size[0]:cut_size[1], cut_size[2]:cut_size[3], cut_size[4]:cut_size[5], :]

		patch_ids = GenerateTfRecord.prepare_validation(T1, patch_size, overlap_stepsize)
		print ('Number of patches:', len(patch_ids))
		writer = tf.io.TFRecordWriter(output_file)

		for i in range(len(patch_ids)):

			(d, h, w) = patch_ids[i]

			_T1 = T1[d:d+patch_size, h:h+patch_size, w:w+patch_size, :]
			#_T2 = T2[d:d+patch_size, h:h+patch_size, w:w+patch_size, :]
			_label = label[d:d+patch_size, h:h+patch_size, w:w+patch_size, :]

			example = tf.train.Example(features=tf.train.Features(
				feature={
					'image': GenerateTfRecord._bytes_feature([_T1[:,:,:,0].tostring()]), #int16
					#'T2': GenerateTfRecord._bytes_feature([_T2[:,:,:,0].tostring()]), #int16
					'label': GenerateTfRecord._bytes_feature([_label[:,:,:,0].tostring()]), #uint8
				}
			))

			writer.write(example.SerializeToString())

		writer.close()


	def write_prediction_examples(T1, patch_size, cut_size, overlap_stepsize, output_file):
		"""Create a testing tfrecord file.

		Args:
			T1: T1 image. [Depth, Height, Width, 1].
			T2: T2 image. [Depth, Height, Width, 1].
			patch_size: An integer.
			cut_size: A list of six integers [Depth_s, Depth_e, Height_s, Height_e, Width_s, Width_e].
			overlap_stepsize: An integer.
			output_file: The file name for the tfrecord file.
		"""

		T1 = T1[cut_size[0]:cut_size[1], cut_size[2]:cut_size[3], cut_size[4]:cut_size[5], :]
		#T2 = T2[cut_size[0]:cut_size[1], cut_size[2]:cut_size[3], cut_size[4]:cut_size[5], :]

		patch_ids = GenerateTfRecord.prepare_validation(T1, patch_size, overlap_stepsize)
		print ('Number of patches:', len(patch_ids))
		writer = tf.io.TFRecordWriter(output_file)

		for i in range(len(patch_ids)):

			(d, h, w) = patch_ids[i]

			_T1 = T1[d:d+patch_size, h:h+patch_size, w:w+patch_size, :]
			#_T2 = T2[d:d+patch_size, h:h+patch_size, w:w+patch_size, :]

			example = tf.train.Example(features=tf.train.Features(
				feature={
					'image': GenerateTfRecord._bytes_feature([_T1[:,:,:,0].tostring()]), #int16
					#'T2': GenerateTfRecord._bytes_feature([_T2[:,:,:,0].tostring()]), #int16
				}
			))

			writer.write(example.SerializeToString())

		writer.close()


	def generate_files(raw_data_dir, output_path, valid_id, pred_id, patch_size, overlap_stepsize):
		"""Create tfrecord files."""
		if valid_id not in range(1, 7) and valid_id != -1:
			print('The valid_id should be in [1,6] or -1.')
			sys.exit(-1)

		if not os.path.exists(output_path):
			os.makedirs(output_path)

		for i in range(1, 7, 1):
			print('---Process subject %d:---' % i)

			subject_name = 'subject-%d' % i
			train_filename = os.path.join(output_path, subject_name+'.tfrecords')

			pred_subject_name = 'subject-%d-pred-%d-patch-%d' % (pred_id, overlap_stepsize, patch_size)
			pred_filename = os.path.join(output_path, pred_subject_name+'.tfrecords')

			valid_subject_name = 'subject-%d-valid-%d-patch-%d' % (valid_id, overlap_stepsize, patch_size)
			valid_filename = os.path.join(output_path, valid_subject_name+'.tfrecords')

			# save converted label for fast evaluation
			converted_label_filename = 'subject-%d-label.npy' % valid_id
			converted_label_filename = os.path.join(output_path, converted_label_filename)

			if (i < 7 and not os.path.isfile(train_filename)) or \
				(i == pred_id and not os.path.isfile(pred_filename)) or \
				(i == valid_id and (not os.path.isfile(valid_filename) or \
					not os.path.isfile(converted_label_filename))):
				print('Loading data...')
				[_T1, _label] = GenerateTfRecord.load_subject(raw_data_dir, i)

				if _label is not None:
					print('Converting label...')
					GenerateTfRecord.convert_labels(_label)
					print('Check label: ', np.max(_label))

				(original_shape, cut_size) = GenerateTfRecord.cut_edge(_T1)
				print('Check original_shape: ', original_shape)
				print('Check cut_size: ', cut_size)

			if (not os.path.isfile(train_filename)) and ((i != valid_id) and (i != pred_id)):
				print('Create the training file:')
				GenerateTfRecord.write_training_examples(_T1, _label, original_shape, cut_size, train_filename)

			if i == valid_id:
				if not os.path.isfile(valid_filename):
					print('Create the validation file:')
					GenerateTfRecord.write_validation_examples(_T1, _label, patch_size, cut_size, overlap_stepsize, valid_filename)

				if not os.path.isfile(converted_label_filename):
					print('Create the converted label file:')
					np.save(converted_label_filename, _label[:,:,:,0])

			if i == pred_id:
				if not os.path.isfile(pred_filename):
					print('Create the prediction file:')
					GenerateTfRecord.write_prediction_examples(_T1, patch_size, cut_size, overlap_stepsize, pred_filename)

			print('---Done.---')

	"""
	if __name__ == '__main__':
		generate_files(
			conf.raw_data_dir,
			conf.data_dir,
			conf.validation_id,
			conf.prediction_id,
			conf.patch_size,
			conf.overlap_step)
	"""
