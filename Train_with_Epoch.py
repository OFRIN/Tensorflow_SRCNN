# Copyright (C) 2020 * Ltd. All rights reserved.
# author : SangHyeon Jo <josanghyeokn@gmail.com>

import os
import cv2
import glob
import time
import argparse

import numpy as np
import tensorflow as tf

from queue import Queue

from core.SRCNN import *

from utils.Utils import *

def parse_args():
    parser = argparse.ArgumentParser(description='SRCNN', formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument('--use_gpu', dest='use_gpu', help='use gpu', default='0', type=str)
    
    parser.add_argument('--scale', dest='scale', help='scale', default=3, type=int)
    parser.add_argument('--stride', dest='stride', help='stride', default=14, type=int)
    
    parser.add_argument('--image_size', dest='image_size', help='image_size', default=32, type=int)
    parser.add_argument('--batch_size', dest='batch_size', help='batch_size', default=128, type=int)

    parser.add_argument('--optimizer', dest='optimizer', help='optimizer', default='SGD', type=str)
    parser.add_argument('--learning_rate', dest='learning_rate', help='learning_rate', default=1e-4, type=floastride
    
    parser.add_argument('--save_epoch', dest='save_epoch', help='save_epoch', default=100, type=int)
    parser.add_argument('--max_epoch', dest='max_epoch', help='max_epoch', default=15000, type=int)

    return parser.parse_args()

##########################################################################################################
# 모든 파라미터를 준비하고, 중요한 정보는 저장합니다.
##########################################################################################################
args = vars(parse_args())

os.environ["CUDA_VISIBLE_DEVICES"] = args['use_gpu']

folder_name = 'SRCNN_image={}x{}_batch={}_optimizer={}_lr={}_stride={}'.format(args['image_size'], args['image_size'], args['batch_size'], args['optimizer'], args['learning_rate'], args['stride'])

model_dir = './experiments/model/{}/'.format(folder_name)
ckpt_format = model_dir + '{}.ckpt'
log_txt_path = model_dir + 'log.txt'
tensorboard_path = './experiments/tensorboard/{}'.format(folder_name)

if not os.path.isdir(model_dir):
    os.makedirs(model_dir)

open(log_txt_path, 'w').close()

##########################################################################################################
# 데이터셋을 불러옵니다.
##########################################################################################################
for image_path in  glob.glob('./dataset/train/*'):
    image = cv2.imread(image_path)
    if image is None:
        print(image_path)
        continue

    h, w, c = image.shape

    input = 

    for x in range(0, h-args['image_size']+1, args['image_size']):
        for y in range(0, w-args['image_size']+1, config.stride):
            sub_input = input_[x:x+config.image_size, y:y+config.image_size] # [33 x 33]
            sub_label = label_[x+int(padding):x+int(padding)+config.label_size, y+int(padding):y+int(padding)+config.label_size] # [21 x 21]

            # Make channel value
            sub_input = sub_input.reshape([config.image_size, config.image_size, 1])  
            sub_label = sub_label.reshape([config.label_size, config.label_size, 1])

            sub_input_sequence.append(sub_input)
            sub_label_sequence.append(sub_label)
            
log_print('# train length : {}'.format(len(image_paths)), log_txt_path)

##########################################################################################################
# Loss, Optimizer 등 학습에 필요한 내용들을 준비합니다.
##########################################################################################################
image_var = tf.placeholder(tf.float32, [None, args['image_size'], args['image_size'], 3])
label_var = tf.placeholder(tf.float32, [None, args['image_size'], args['image_size'], 3])

predictions_op = SRCNN(image_var, {
    'use_sigmoid' : True,
    
    'conv1' : dict(filters = 64, kernel_size = (9, 9), strides = 1, padding = 'same', name = 'conv1'),
    'conv2' : dict(filters = 32, kernel_size = (1, 1), strides = 1, padding = 'same', name = 'conv2'),
    'conv3' : dict(filters = 3, kernel_size = (3, 3), strides = 1, padding = 'same', name = 'conv3'),
})

loss_op = tf.reduce_mean(tf.square(label_var - predictions_op))

if args['optimizer'] == 'SGD':
    train_op = tf.train.GradientDescentOptimizer(args['learning_rate']).minimize(loss_op)
else:
    assert False, "[!] Optimizer"

##########################################################################################################
# 디버깅을 위한 Tensorboard를 준비합니다.
##########################################################################################################
tf.summary.scalar('Loss', loss_op)
train_summary_op = tf.summary.merge_all()

##########################################################################################################
# 학습 전 GPU 메모리를 할당받습니다.
##########################################################################################################
sess = tf.Session()
sess.run(tf.global_variables_initializer())

saver = tf.train.Saver(max_to_keep = 1)

train_writer = tf.summary.FileWriter(tensorboard_path)

##########################################################################################################
# 데이터 전처리를 빠르게 도와주는 스레드를 생성합니다.
##########################################################################################################
main_queue = Queue(100 * args['num_threads'])

thread_option = {
    'main_queue' : main_queue,
    'image_size' : args['image_size'],
    'batch_size' : args['batch_size'],

    'image_paths' : image_paths,

    'min_scale' : args['min_scale'],
    'max_scale' : args['max_scale'],

    'crop_per_image' : args['crop_per_image'],
}

train_threads = []
for i in range(args['num_threads']):
    th = Teacher(thread_option)
    th.start()

    train_threads.append(th)

##########################################################################################################
# 학습 하는 부분입니다.
##########################################################################################################
train_ops = [train_op, loss_op, train_summary_op]

loss_list = []
train_time = time.time()

for iter in range(1, args['max_epoch'] + 1):
    batch_image_data, batch_label_data = main_queue.get()

    _feed_dict = {
        image_var : batch_image_data,
        label_var : batch_label_data,
    }
    _, loss, summary = sess.run(train_ops, feed_dict = _feed_dict)
    train_writer.add_summary(summary, iter)

    loss_list.append(loss)

    if iter % args['log_iteration'] == 0:
        loss = np.mean(loss_list)
        train_time = int(time.time() - train_time)

        log_print('[i] iter = {}, loss = {:.4f}, train_time = {}sec'.format(iter, loss, train_time), log_txt_path)

        loss_lsit = []
        train_time = time.time()

    if iter % args['save_epoch'] == 0:
        saver.save(sess, ckpt_format.format(iter))

for th in train_threads:
    th.train = False
    th.join()

saver.save(sess, ckpt_format.format('end'))