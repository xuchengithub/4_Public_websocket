# -*- coding: utf-8 -*-
"""
Created on Thu Jul 23 07:33:21 2020

@author: xuchen
"""

# import the necessary packages
import numpy as np
import imutils#主要是用来进行图形图像的处理，如图像的平移、旋转、缩放、骨架提取、显示等等，后期又加入了针对视频的处理，如摄像头、本地文件等
import cv2
class SingleMotionDetector:
    #初始函数
    def __init__(self, accumWeight=0.5):
        # store the accumulated weight factor
        self.accumWeight = accumWeight
        # initialize the background model
        self.bg = None
    #图像加权函数
    #accumWeight越大，在累积加权平均值时，背景(bg)被考虑的越少。
    #相反地，accumWeight越小，在计算平均值时考虑背景(bg)就会越多
    def update(self, image):
    		# if the background model is None, initialize it
        if self.bg is None:
            self.bg = image.copy().astype("float")
            return
    		# update the background model by accumulating the weighted
    		# average
        cv2.accumulateWeighted(image,self.bg,self.accumWeight)
    
    def detect(self, image, tVal=25):
    		# compute the absolute difference between the background model
    		# and the image passed in, then threshold the delta image
        delta = cv2.absdiff(self.bg.astype("uint8"), image)
        thresh = cv2.threshold(delta, tVal, 255, cv2.THRESH_BINARY)[1]
    		# perform a series of erosions and dilations to remove small
    		# blobs
        #腐蚀
        thresh = cv2.erode(thresh, None, iterations=2)
        thresh = cv2.dilate(thresh, None, iterations=2)
        
        # find contours（轮廓） in the thresholded image and initialize（初始化） the
    		# minimum and maximum bounding box regions for motion
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,#返回最外层的
                            cv2.CHAIN_APPROX_SIMPLE)#压缩水平方向，垂直方向，对角线方向的元素，只保留该方向的终点坐标，例如一个矩形轮廓只需4个点来保存轮廓信息
        
        cnts = imutils.grab_contours(cnts)#imutils.grab_contours的作用，返回cnts中的countors(轮廓)
        (minX, minY) = (np.inf, np.inf)
        (maxX, maxY) = (-np.inf, -np.inf)
        # if no contours were found, return None
        if len(cnts) == 0:
            return None
		# otherwise, loop over the contours
        for c in cnts:
			# compute the bounding box of the contour and use it to
			# update the minimum and maximum bounding box regions
            (x, y, w, h) = cv2.boundingRect(c)
            (minX, minY) = (min(minX, x), min(minY, y))
            (maxX, maxY) = (max(maxX, x + w), max(maxY, y + h))
        # otherwise, return a tuple of the thresholded image along
        # with bounding box
        return (thresh, (minX, minY, maxX, maxY))