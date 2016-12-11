import tensorflow as tf
from genericModel import *
from utils import *
from nn_utils import weight_variable, bias_variable, conv2d, max_pool_2x2, add_last_layer
from nn_utils import test_object_detection_spherical_softmax, test_object_detection_softmax
import os, sys
import numpy as np
from PIL import Image, ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
from random import shuffle
import argparse
import random
import matplotlib.pyplot as plt

def parse_args():
	parser = argparse.ArgumentParser()
	parser.add_argument('--MAINFILE_PATH', type=str, help='The main path where the codebase exists')
	parser.add_argument('--batch_size', type=int, help='Batch size for training')
	parser.add_argument('--num_epochs', type=int, help='Number of epochs to be trained for', default = 1)
	parser.add_argument('--positiveImages_path_textfile', type=str)
	parser.add_argument('--negativeImages_path_textfile', type=str)
	parser.add_argument('--positiveImagesDirName', type = str)
	parser.add_argument('--negativeImagesDirName', type = str)
	parser.add_argument('--SAVED_NETWORKS_PATH', type = str)
	parser.add_argument('--background_fraction', type=float, default= 0.2)
	parser.add_argument('--class_count', type=int, default=21)
	parser.add_argument('--learning_rate', type=float, default = 1e-5)
	parser.add_argument('--lamb', type=float, default=1.0)
	parser.add_argument('--GPUFrac', type=float)
	parser.add_argument('--sphericalLossType', type=str, default='spherical_hinge_loss')
	parser.add_argument('--train_or_test', type=str, default='train')
	args = parser.parse_args()
	ensure_dir_exists(args.SAVED_NETWORKS_PATH)

	params_file = open(os.path.join(args.SAVED_NETWORKS_PATH, 'training_params.txt'), 'w')
	params_file.write('Batch size used: {}\n'.format(args.batch_size))
	params_file.write('Num Epochs to be trained for: {}\n'.format(args.num_epochs))
	params_file.write('Positive Images textfile name: {}\n'.format(args.positiveImages_path_textfile))
	params_file.write('Negative Images textfile name: {}\n'.format(args.negativeImages_path_textfile))
	params_file.write('Positive Images Directory: {}\n'.format(args.positiveImagesDirName))
	params_file.write('Negative Images Directory: {}\n'.format(args.negativeImagesDirName))
	params_file.write('Saved networks path: {}\n'.format(args.SAVED_NETWORKS_PATH))
	params_file.write('background_fraction: {}\n'.format(args.background_fraction))
	params_file.write('Class count: {}\n'.format(args.class_count))
	params_file.write('Learning rate: {}\n'.format(args.learning_rate))
	params_file.write('lambda: {}\n'.format(args.lamb))
	params_file.write('GPU Frac Used: {}\n'.format(args.GPUFrac))
	params_file.write('Spherical Loss used: {}\n'.format(args.sphericalLossType))
	params_file.close()
	return args

def get_all_paths_and_labels(textFilePath, ImagesDirName):
	ImagePaths = []
	ImageLabels = []
	f = open(textFilePath, 'r')

	allLines = f.readlines()
	index_shuff = range(len(allLines))
	shuffle(index_shuff)

	for i in index_shuff:
		line = allLines[i]
		line = line.split()
		ImagePaths.append(os.path.join(args.MAINFILE_PATH, ImagesDirName, line[0]))
		ImageLabels.append(int(line[1]))

	return ImagePaths, ImageLabels


args = parse_args()

##################################################################################

gpu_options = tf.GPUOptions(per_process_gpu_memory_fraction=args.GPUFrac)
sess = tf.InteractiveSession(config=tf.ConfigProto(gpu_options=gpu_options))

################## Initialise a model ############################################

Model = generic_model(args.class_count)
object_or_not, labelTensor, imgTensor, scores, h_fc1 = Model.build_basic_graph(sess)
cross_entropy, sphere_loss, train_step, norm_squared, object_score = Model.build_graph_for_target(sess, labelTensor, scores, \
													h_fc1, object_or_not, args.learning_rate, args.lamb, args.sphericalLossType)

#######################################################################################

positiveImagePaths, positiveImageLabels = get_all_paths_and_labels(args.positiveImages_path_textfile, args.positiveImagesDirName)
negativeImagePaths, negativeImageLabels = get_all_paths_and_labels(args.negativeImages_path_textfile, args.negativeImagesDirName)

#############################################################################################
saver = tf.train.Saver()

sess.run(tf.initialize_all_variables())

checkpoint = tf.train.get_checkpoint_state(args.SAVED_NETWORKS_PATH)
if checkpoint and checkpoint.model_checkpoint_path:
	checkpoint_IterNum = int(checkpoint.model_checkpoint_path.split('-')[-1])
	saver.restore(sess, checkpoint.model_checkpoint_path)
	print "Successfully loaded:", checkpoint.model_checkpoint_path
else:
	checkpoint_IterNum = 0
	print "Could not find old network weights"
##########################################################################################

if args.train_or_test == 'train':

	num_positive_images = len(positiveImageLabels)
	num_negative_images = len(negativeImageLabels)

	positive_batch_size = int((1 - args.background_fraction)*args.batch_size)
	negative_batch_size = args.batch_size - positive_batch_size

	for epoch_num in range(args.num_epochs):
		
		for positive_batch_iter in range(0, num_positive_images, positive_batch_size):
			positive_start = positive_batch_iter
			positive_end = min(num_positive_images, positive_batch_iter + positive_batch_size)
			image_inputs = []
			label_inputs_one_hot = np.zeros((args.batch_size, args.class_count))
			object_or_not_inputs = []

			for image_iter in range(positive_start, positive_end):
				# image_input = Image.open(positiveImagePaths[image_iter]).resize((299, 299))
				image_input = Image.open(positiveImagePaths[image_iter]).resize((80, 80))		
				image_input = image_input.convert('RGB')
				image_input = np.array(image_input)

				label_index = positiveImageLabels[image_iter]

				image_inputs.append(image_input)
				label_inputs_one_hot[image_iter - positive_start, label_index] = 1
				object_or_not_inputs.append(1)

			negative_minibatch = random.sample(range(num_negative_images), args.batch_size - (positive_end - positive_start))
			for i, index in enumerate(negative_minibatch):
				image_input = Image.open(negativeImagePaths[index]).resize((80,80))
				image_input = image_input.convert('RGB')
				image_input = np.array(image_input)

				label_index = negativeImageLabels[index]

				image_inputs.append(image_input)
				label_inputs_one_hot[positive_end - positive_start + i, label_index] = 1
				object_or_not_inputs.append(0)

			train_step.run(feed_dict = {labelTensor: label_inputs_one_hot, imgTensor: image_inputs, object_or_not: object_or_not_inputs})
			h_fc1_value, cross_entropy_value, sphere_loss_value, norm_squared_value = sess.run([h_fc1, cross_entropy, sphere_loss, norm_squared], feed_dict = {labelTensor: label_inputs_one_hot, imgTensor: image_inputs, object_or_not: object_or_not_inputs})
		
		print 'epoch number: {}'.format(epoch_num) +' done with training cross entropy loss = ' + str(cross_entropy_value) + ' and with training hinge loss = ' + str(sphere_loss_value)	
		if epoch_num % 10 == 0:
			saver.save(sess, args.SAVED_NETWORKS_PATH + '/' + 'weights', global_step = (epoch_num+1)*num_positive_images + checkpoint_IterNum)

elif agrs.train_or_test == 'test':
