import tensorflow as tf


"""This script defines hyperparameters.
"""

class Configure():
	# training
	raw_data_dir = '/data/zhengyang/InfantBrain/RawData' # 'the directory where the raw data is stored'
	data_dir = '/data/zhengyang/InfantBrain/tfrecords_full' # 'the directory where the input data is stored'
	num_training_subs = 9 # 'the number of subjects used for training'
	train_epochs = 10000 # 'the number of epochs to use for training'
	epochs_per_eval = 50 # 'the number of training epochs to run between evaluations'
	batch_size = 5 # 'the number of examples processed in each training batch'
	learning_rate = 1e-3 # 'learning rate'
	weight_decay = 2e-6 # 'weight decay rate'
	num_parallel_calls = 5 # 'The number of records that are processed in parallel \
			    # during input processing. This can be optimized per data set but \
			    # for generally homogeneous data sets, should be approximately the \
			    # number of available CPU cores.')
	model_dir = '/kaggle/working/model-10' # 'the directory where the model will be stored'

	# validation / prediction
	patch_size = 32 # 'spatial size of patches'
	overlap_step = 8 # 'overlap step size when performing validation/prediction'
	validation_id = 10 # '1-10 or -1, which subject is used for validation'
	prediction_id = 11 # '1-23, which subject is used for prediction'
	checkpoint_num = 1530 # 'which checkpoint is used for validation/prediction'
	save_dir = '/kaggle/working/results' # 'the directory where the prediction is stored'

	# network
	network_depth = 3 # 'the network depth'
	num_classes = 4 # 'the number of classes'
	num_filters = 32 # 'number of filters for initial_conv'

	
	def display(self):
		"""Display Configuration values."""
		print("\nConfigurations:")
		for a in dir(self):
		    if not a.startswith("__") and not callable(getattr(self, a)):
			print("{:30} {}".format(a, getattr(self, a)))
		print("\n")
