import numpy as np
import os, sys
import tensorflow as tf
from utils import *
import xmltodict
from time import sleep


MAINFILE_PATH = '/Users/vishakhhegde/ObjectDetection'
image_dir = os.path.join(MAINFILE_PATH, 'VOCdevkit', 'VOC2012', 'JPEGImages')
cropped_image_dir = os.path.join(MAINFILE_PATH, 'VOCCroppedImages')

xmlFiles_dir = os.path.join(MAINFILE_PATH, 'VOCdevkit', 'VOC2012', 'Annotations')

def get_orig_bbox(xml_filepath):
	xml_file = open(xml_filepath, 'r')
	objDict_list = xmltodict.parse(xml_file)['annotation']['object']
	if not type(objDict_list) is list:
		objDict_list = [objDict_list]
	return objDict_list

def find_IoU(box1, box2):
	inter_xmax = min(box1[0], box2[0])
	inter_xmin = max(box1[1], box2[1])
	inter_ymax = min(box1[2], box2[2])
	inter_ymin = max(box1[3], box2[3])

	check1 = inter_xmax - inter_xmin
	check2 = inter_ymax - inter_ymin
	if check1 < 0 or check2 < 0:
		intersection = 0
		return 0
	else:
		intersection = (inter_xmax - inter_xmin + 1)*(inter_ymax - inter_ymin + 1)
		box1_area = (box1[0] - box1[1] + 1)*(box1[2] - box1[3] + 1)
		box2_area = (box2[0] - box2[1] + 1)*(box2[2] - box2[3] + 1)
		union = box1_area + box2_area - intersection
		IoU = float(intersection)/float(union)
		return IoU

def is_object(bbox, origBbox_list, IoU_threshold = 0.8):
	xmax, xmin, ymax, ymin = bbox
	bbox = (int(xmax), int(xmin), int(ymax), int(ymin))
	object_switch = 0
	for origBbox in origBbox_list:
		orig_xmax = int(origBbox['bndbox']['xmax'])
		orig_xmin = int(origBbox['bndbox']['xmin'])
		orig_ymax = int(origBbox['bndbox']['ymax'])
		orig_ymin = int(origBbox['bndbox']['ymin'])
		orig_bbox = (orig_xmax, orig_xmin, orig_ymax, orig_ymin)
		IoU = find_IoU(orig_bbox, bbox)
		if IoU > IoU_threshold:
			object_switch = 1
			return origBbox['name'], object_switch
	return 'background', object_switch

def crop_single_image(orig_img, bbox):
	x_max,x_min,y_max,y_min = bbox
	cropped_img = orig_img[x_min:x_max, y_min:y_max]
	return cropped_img

def crop_all_images_in_dict(bbox_dictionary, image_dir, cropped_image_dir, xmlFiles_dir):
	ensure_dir_exists(cropped_image_dir)
	existing_cropped_image_list = os.listdir(cropped_image_dir)
	for image_name in bbox_dictionary:
		xml_filepath = os.path.join(xmlFiles_dir, image_name + '.xml')
		origBbox_list = get_orig_bbox(xml_filepath)
		
		image_path = os.path.join(image_dir, image_name + '.jpg')
		orig_img = cv2.imread(image_path)

		for j, origBbox in enumerate(origBbox_list):
			orig_xmax = int(origBbox['bndbox']['xmax'])
			orig_xmin = int(origBbox['bndbox']['xmin'])
			orig_ymax = int(origBbox['bndbox']['ymax'])
			orig_ymin = int(origBbox['bndbox']['ymin'])
			orig_bbox = orig_bbox = (orig_xmax, orig_xmin, orig_ymax, orig_ymin)
			cropped_img = crop_single_image(orig_img, orig_bbox)
			cropped_img_name = image_name + '_orig_' + str(j) + '.jpg'
			cv2.imwrite(os.path.join(cropped_image_dir, cropped_img_name), cropped_img)
			sleep(0.01)
			print cropped_img_name, origBbox['name']

		for i, bbox in enumerate(bbox_dictionary[image_name]):
			object_class, object_switch = is_object(bbox, origBbox_list)			
			cropped_img_name = image_name + '_' + str(i) + '.jpg'

			# Now we actually need to crop the image
			cropped_img = crop_single_image(orig_img, bbox)
			cv2.imwrite(os.path.join(cropped_image_dir, cropped_img_name), cropped_img)
			sleep(0.01)
			if object_switch > 0:
				print cropped_img_name, object_class

#######################################################################################

# Get a dictionary of bounding boxes
bbox_dictionary = get_regions_dictionary('/Users/vishakhhegde/ObjectDetection/selective_search_data/voc_2012_train.mat',image_dir)

# Crop all images
crop_all_images_in_dict(bbox_dictionary, image_dir, cropped_image_dir, xmlFiles_dir)

######################################################################################




