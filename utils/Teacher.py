# Copyright (C) 2020 * Ltd. All rights reserved.
# author : SangHyeon Jo <josanghyeokn@gmail.com>

import cv2
import copy
import time
import random

import numpy as np

from threading import Thread

from utils.Utils import *
from utils.Timer import *

class Teacher(Thread):
    
    def __init__(self, train_data_list, batch_size, main_queue):
        Thread.__init__(self)

        self.train = True
        self.watch = StopWatch()
        self.main_queue = main_queue
        
        self.batch_size = batch_size
        self.train_data_list = copy.deepcopy(train_data_list)

        self.augment = RandAugment()
        
    def run(self):
        while self.train:
            while self.main_queue.full() and self.train:
                time.sleep(0.1)
                continue
            
            batch_image_data = []
            batch_label_data = []

            np.random.shuffle(self.train_data_list)
            batch_data_list = self.train_data_list[:self.batch_size]

            for data in batch_data_list:
                image, label = data
                image = self.augment(image)

                batch_image_data.append(image)
                batch_label_data.append(label)

            batch_image_data = np.asarray(batch_image_data, dtype = np.float32)
            batch_label_data = np.asarray(batch_label_data, dtype = np.float32)
            
            self.main_queue.put([batch_image_data, batch_label_data])
