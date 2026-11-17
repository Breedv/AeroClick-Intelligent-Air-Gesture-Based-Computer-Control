import numpy as np
import cv2
import cv2.aruco as aruco
import os
import glob
import math
import pyautogui
import time

class Marker:
    def __init__(self, dict_type = aruco.DICT_4X4_50, thresh_constant = 1):
        self.aruco_dict = aruco.getPredefinedDictionary(dict_type)
        self.parameters = aruco.DetectorParameters()
        self.parameters.adaptiveThreshConstant = thresh_constant
        self.corners = None # corners of Marker
        self.marker_x2y = 1 # width:height ratio
        self.detector = aruco.ArucoDetector(self.aruco_dict, self.parameters)
    
    def calibrate():
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)
        objp = np.zeros((6*7,3), np.float32)
        objp[:,:2] = np.mgrid[0:7,0:6].T.reshape(-1,2)
        objpoints = [] # 3d point in real world space
        imgpoints = [] # 2d points in image plane.
        path = os.path.dirname(os.path.abspath(__file__))
        p1 = path + r'\calib_images\checkerboard\*.jpg'
        images = glob.glob(p1)
        for fname in images:
            img = cv2.imread(fname)
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            ret, corners = cv2.findChessboardCorners(gray, (7,6),None)
            if ret == True:
                objpoints.append(objp)
                corners2 = cv2.cornerSubPix(gray,corners,(11,11),(-1,-1),criteria)
                imgpoints.append(corners2)
                img = cv2.drawChessboardCorners(img, (7,6), corners2,ret)
                
        ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1],None,None)
        
        #mtx = [[534.34144579,0.0,339.15527836],[0.0,534.68425882,233.84359493],[0.0,0.0,1.0]]
        #dist = [[-2.88320983e-01, 5.41079685e-02, 1.73501622e-03, -2.61333895e-04, 2.04110465e-01]]
        return mtx, dist
    
    def detect(self, frame):
        gray_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        self.corners, ids, _ = self.detector.detectMarkers(gray_frame)
        if ids is None:
            self.corners = None

    def is_detected(self):
        if self.corners:
            return True
        return False
    
    def draw_marker(self, frame):
        aruco.drawDetectedMarkers(frame, self.corners)
    
        

def ecu_dis(p1, p2):
    dist = np.sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)
    return dist

def find_HSV(samples):
    try:
        color = np.uint8([ samples ])
    except:
        color = np.uint8([ [[105,105,50]] ])
    hsv_color = cv2.cvtColor(color,cv2.COLOR_RGB2HSV)
    #print( hsv_color )
    return hsv_color

def draw_box(frame, points, color=(0,255,127)):
    if points:
        frame = cv2.line(frame, points[0], points[1], color, thickness=2, lineType=8) #top
        frame = cv2.line(frame, points[1], points[2], color, thickness=2, lineType=8) #right
        frame = cv2.line(frame, points[2], points[3], color, thickness=2, lineType=8) #bottom
        frame = cv2.line(frame, points[3], points[0], color, thickness=2, lineType=8) #left

def in_cam(val, type_):
    if type_ == 'x':
        if val<0:
            return 0
        if val>GestureController.cam_width:
            return GestureController.cam_width
    elif type_ == 'y':
        if val<0:
            return 0
        if val>GestureController.cam_height:
            return GestureController.cam_height
    return val

    
class ROI:
    def __init__(self, roi_alpha1=1.5, roi_alpha2=1.5, roi_beta=2.5, hsv_alpha = 0.3, hsv_beta = 0.5, hsv_lift_up = 0.3):
        self.roi_alpha1 = roi_alpha1
        self.roi_alpha2 = roi_alpha2
        self.roi_beta = roi_beta
        self.roi_corners = None
        
        self.hsv_alpha = hsv_alpha
        self.hsv_beta = hsv_beta
        self.hsv_lift_up = hsv_lift_up
        self.hsv_corners = None
        
        self.marker_top = None
        self.glove_hsv = None
        
    def findROI(self, frame, marker):
        rec_coor = marker.corners[0][0]
        c1 = (int(rec_coor[0][0]),int(rec_coor[0][1]))
        c2 = (int(rec_coor[1][0]),int(rec_coor[1][1]))
        c3 = (int(rec_coor[2][0]),int(rec_coor[2][1]))
        c4 = (int(rec_coor[3][0]),int(rec_coor[3][1]))
        
        try:
            marker.marker_x2y = np.sqrt((c1[0]-c2[0])**2 + (c1[1]-c2[1])**2) / np.sqrt((c3[0]-c2[0])**2 + (c3[1]-c2[1])**2)
        except:
            marker.marker_x2y = 999.0
        
        #mid-point of top line of Marker
        cx = (c1[0] + c2[0])/2
        cy = (c1[1] + c2[1])/2
        
        self.marker_top = [cx, cy]
        
        l = np.absolute(ecu_dis(c1,c4))
        
        try:
            slope_12 = (c1[1]-c2[1])/(c1[0]-c2[0])
        except:
            slope_12 = (c1[1]-c2[1])*999.0 + 0.1
        
        try:
            slope_14 = -1 / slope_12
        except:
            slope_14 = -999.0
        
        if slope_14 < 0:
            sign = 1
        else:
            sign = -1
        
        bot_rx = int(cx + self.roi_alpha2 * l * np.sqrt(1/(1+slope_12**2)))
        bot_ry = int(cy + self.roi_alpha2 * slope_12 * l * np.sqrt(1/(1+slope_12**2)))
        
        bot_lx = int(cx - self.roi_alpha1 * l * np.sqrt(1/(1+slope_12**2)))
        bot_ly = int(cy - self.roi_alpha1 * slope_12 * l * np.sqrt(1/(1+slope_12**2)))
        
        top_lx = int(bot_lx + sign * self.roi_beta * l * np.sqrt(1/(1+slope_14**2)))
        top_ly = int(bot_ly + sign * self.roi_beta * slope_14 * l * np.sqrt(1/(1+slope_14**2)))
        
        top_rx = int(bot_rx + sign * self.roi_beta * l * np.sqrt(1/(1+slope_14**2)))
        top_ry = int(bot_ry + sign * self.roi_beta * slope_14 * l * np.sqrt(1/(1+slope_14**2)))
        
        bot_lx = in_cam(bot_lx, 'x')
        bot_ly = in_cam(bot_ly, 'y')
        
        bot_rx = in_cam(bot_rx, 'x')
        bot_ry = in_cam(bot_ry, 'y')
        
        top_lx = in_cam(top_lx, 'x')
        top_ly = in_cam(top_ly, 'y')
        
        top_rx = in_cam(top_rx, 'x')
        top_ry = in_cam(top_ry, 'y')
        
        self.roi_corners = [(bot_lx,bot_ly), (bot_rx,bot_ry), (top_rx,top_ry), (top_lx,top_ly)]
        
        
    def find_glove_hsv(self, frame, marker):
        rec_coor = marker.corners[0][0]
        c1 = (int(rec_coor[0][0]),int(rec_coor[0][1]))
        c2 = (int(rec_coor[1][0]),int(rec_coor[1][1]))
        c3 = (int(rec_coor[2][0]),int(rec_coor[2][1]))
        c4 = (int(rec_coor[3][0]),int(rec_coor[3][1]))
        
        l = np.absolute(ecu_dis(c1,c4))
        
        try:
            slope_12 = (c1[1]-c2[1])/(c1[0]-c2[0])
        except:
            slope_12 = (c1[1]-c2[1])*999.0 + 0.1
        try:
            slope_14 = -1 / slope_12
        except:
            slope_14 = -999.0
        
        if slope_14 < 0:
            sign = 1
        else:
            sign = -1
               
        bot_rx = int(self.marker_top[0] + self.hsv_alpha * l * np.sqrt(1/(1+slope_12**2)))
        bot_ry = int(self.marker_top[1] - self.hsv_lift_up*l + self.hsv_alpha * slope_12 * l * np.sqrt(1/(1+slope_12**2)))
        
        bot_lx = int(self.marker_top[0] - self.hsv_alpha * l * np.sqrt(1/(1+slope_12**2)))
        bot_ly = int(self.marker_top[1] - self.hsv_lift_up*l - self.hsv_alpha * slope_12 * l * np.sqrt(1/(1+slope_12**2)))
        
        top_lx = int(bot_lx + sign * self.hsv_beta * l * np.sqrt(1/(1+slope_14**2)))
        top_ly = int(bot_ly + sign * self.hsv_beta * slope_14 * l * np.sqrt(1/(1+slope_14**2)))
        
        top_rx = int(bot_rx + sign * self.hsv_beta * l * np.sqrt(1/(1+slope_14**2)))
        top_ry = int(bot_ry + sign * self.hsv_beta * slope_14 * l * np.sqrt(1/(1+slope_14**2)))
        
        region = frame[min(top_ry,bot_ry):max(top_ry,bot_ry), min(top_lx,bot_rx):max(top_lx,bot_rx)]
        if region.size == 0:
            raise ValueError("Glove color region is outside the frame")
        b, g, r = np.mean(region, axis=(0, 1))
        
        self.hsv_glove = find_HSV([[r,g,b]])
        self.hsv_corners =  [(bot_lx,bot_ly), (bot_rx,bot_ry), (top_rx,top_ry), (top_lx,top_ly)]
        
    
    def cropROI(self, frame):
        pts = np.array(self.roi_corners)
        
        ## (1) Crop the bounding rect
        rect = cv2.boundingRect(pts)
        x,y,w,h = rect
        croped = frame[y:y+h, x:x+w].copy()
        
        ## (2) make mask
        pts = pts - pts.min(axis=0)
        
        mask = np.zeros(croped.shape[:2], np.uint8)
        cv2.drawContours(mask, [pts], -1, (255, 255, 255), -1, cv2.LINE_AA)
        
        ## (3) do bit-op
        dst = cv2.bitwise_and(croped, croped, mask=mask)
        
        ## (4) add the white background
        bg = np.ones_like(croped, np.uint8)*255
        cv2.bitwise_not(bg,bg, mask=mask)
        
        kernelOpen = np.ones((3,3),np.uint8)
        kernelClose = np.ones((5,5),np.uint8)
        
        hsv = cv2.cvtColor(dst, cv2.COLOR_BGR2HSV)
        
        lower_range = np.array([self.hsv_glove[0][0][0]//1-5,50,50])
        upper_range = np.array([self.hsv_glove[0][0][0]//1+5,255,255])
        
        mask = cv2.inRange(hsv, lower_range, upper_range)
        #mask = cv2.dilate(mask,kernelOpen,iterations = 1)
        Opening =cv2.morphologyEx(mask,cv2.MORPH_OPEN,kernelOpen)
        Closing =cv2.morphologyEx(Opening,cv2.MORPH_CLOSE,kernelClose)
        FinalMask = Closing
        
        return FinalMask


class Glove:
    
    def __init__(self):
        self.fingers = 0
        self.arearatio = 0
        self.gesture = 0
    
    def find_fingers(self, FinalMask):
        conts,h=cv2.findContours(FinalMask,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_NONE)
        self.fingers, self.arearatio = 0, 0
        defects = None
        
        try:
            cnt = max(conts, key = lambda x: cv2.contourArea(x))
            #approx the contour a little
            epsilon = 0.0005*cv2.arcLength(cnt,True)
            approx= cv2.approxPolyDP(cnt,epsilon,True)
            #make convex hull around hand
            hull = cv2.convexHull(cnt)
            #define area of hull and area of hand
            areahull = cv2.contourArea(hull)
            areacnt = cv2.contourArea(cnt)
            #find the percentage of area not covered by hand in convex hull
            self.arearatio=((areahull-areacnt)/areacnt)*100
            #find the defects in convex hull with respect to hand
            hull = cv2.convexHull(approx, returnPoints=False)
            defects = cv2.convexityDefects(approx, hull)
        except:
            return
        
        # l = no. of defects
        l=0
        if defects is None:
            self.fingers = 1
            return
        try:
            #code for finding no. of defects due to fingers
            for i in range(defects.shape[0]):
                s,e,f,d = defects[i,0]
                start = tuple(approx[s][0])
                end = tuple(approx[e][0])
                far = tuple(approx[f][0])
                
                # find length of all sides of triangle
                a = math.sqrt((end[0] - start[0])**2 + (end[1] - start[1])**2)
                b = math.sqrt((far[0] - start[0])**2 + (far[1] - start[1])**2)
                c = math.sqrt((end[0] - far[0])**2 + (end[1] - far[1])**2)
                s = (a+b+c)/2
                ar = math.sqrt(max(0, s*(s-a)*(s-b)*(s-c)))
                
                #distance between point and convex hull
                d=(2*ar)/max(a, 1e-6)
                
                # apply cosine rule here
                angle = math.acos(max(-1, min(1, (b**2 + c**2 - a**2)/max(2*b*c, 1e-6)))) * 57
                      
                # ignore angles > 90 and ignore points very close to convex hull(they generally come due to noise)
                if angle <= 90 and d>30:
                    l += 1
                    #cv2.circle(frame, far, 3, [255,255,255], -1)
                
                #draw lines around hand
                cv2.line(FinalMask,start, end, [255,255,255], 2)
                
            l+=1
        except:
            l = 0
            pass
        
        self.fingers = l
        
    def find_gesture(self, frame):
        font = cv2.FONT_HERSHEY_SIMPLEX
        self.gesture = 0
        if self.fingers==1:
            #cv2.putText(frame, str(int(arearatio)), (10,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
            if self.arearatio<15:
                cv2.putText(frame,'0',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                self.gesture = 0
            elif self.arearatio<25:
                cv2.putText(frame,'2 fingers',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                self.gesture = 2
            else:
                cv2.putText(frame,'1 finger',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                self.gesture = 1
                    
        elif self.fingers==2:
            cv2.putText(frame,'2',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
            self.gesture = 3
        '''
        elif self.fingers==3:
            #cv2.putText(frame,'3',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
                    
        elif self.fingers==4:
            #cv2.putText(frame,'4',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
            
        elif self.fingers==5:
            #cv2.putText(frame,'5',(0,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
            
        else :
           # cv2.putText(frame,'reposition',(10,50), font, 2, (0,0,255), 3, cv2.LINE_AA)
        '''

class Tracker:
    def __init__(self):
        self.tracker_started = False
        self.tracker = None
        self.start_time = 0.0
        self.now_time = 0.0
        self.tracker_bbox = None
        
    def corners_to_tracker(self, corners):
        csrt_minX = int( min( [corners[0][0][0][0], corners[0][0][1][0], corners[0][0][2][0], corners[0][0][3][0]] ))
        csrt_maxX = int( max( [corners[0][0][0][0], corners[0][0][1][0], corners[0][0][2][0], corners[0][0][3][0]] ))
        csrt_minY = int( min( [corners[0][0][0][1], corners[0][0][1][1], corners[0][0][2][1], corners[0][0][3][1]] ))
        csrt_maxY = int( max( [corners[0][0][0][1], corners[0][0][1][1], corners[0][0][2][1], corners[0][0][3][1]] ))
        self.tracker_bbox = [csrt_minX, csrt_minY, csrt_maxX-csrt_minX, csrt_maxY-csrt_minY]
        
    def tracker_to_corner(self, final_bbox):
        if self.tracker_bbox is None:
            return None
        final_bbox = [[[1,2],[3,4],[5,6],[7,8]]]
        final_bbox[0][0] = [self.tracker_bbox[0],self.tracker_bbox[1]]
        final_bbox[0][1] = [self.tracker_bbox[0]+ self.tracker_bbox[2],self.tracker_bbox[1]]
        final_bbox[0][2] = [self.tracker_bbox[0]+ self.tracker_bbox[2],self.tracker_bbox[1] + self.tracker_bbox[3]]
        final_bbox[0][3] = [self.tracker_bbox[0],self.tracker_bbox[1] +self.tracker_bbox[3]]
        return [np.array(final_bbox, dtype = 'f')]
        
    def CSRT_tracker(self, frame):        
        if self.tracker_bbox is None and self.tracker_started == False:
            return
        
        if self.tracker_started == False:
            if self.tracker == None:
                self.tracker = cv2.TrackerCSRT_create()
        
        if self.tracker_bbox is not None and not self.tracker_started:
            try:
                self.start_time = time.time()
                ok = self.tracker.init(frame, tuple(int(v) for v in self.tracker_bbox))
                self.tracker_started = True
            except:
                print("tracker.init failed")
        try:
            ok, self.tracker_bbox = self.tracker.update(frame)
        except:
            ok = None
            print("tracker.update failed")
        self.now_time = time.time()
        
        if self.now_time-self.start_time >= 2.0 :
            #cv2.putText(frame, "Please posture your hand correctly", (10,50), cv2.FONT_HERSHEY_SIMPLEX, 1,(0,0,255),1)
            cv2.putText(frame,'Posture your hand correctly',(10,10), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (0,0,255), 1, cv2.LINE_AA)
            #print("tracking timeout")
            self.tracker_started = False
            self.tracker_bbox = None
            return
            
        if ok:
            # Tracking success
            p1 = (int(self.tracker_bbox[0]), int(self.tracker_bbox[1]))
            p2 = (int(self.tracker_bbox[0] + self.tracker_bbox[2]), int(self.tracker_bbox[1] + self.tracker_bbox[3]))
            cv2.rectangle(frame, p1, p2, (80, 255, 255), 2, 1)
        else :
            # Tracking failure
            self.tracker_started = False
            cv2.putText(frame, "Tracking failure detected", (100,80), cv2.FONT_HERSHEY_SIMPLEX, 0.75,(0,0,255),2)
            print("Tracking failure detected")
            #reintiallize code to tackle tracking failure
            
    
        
        
        

# Compatibility dimensions used by the original ROI geometry above.
class GestureController:
    cam_width = 640
    cam_height = 480


class GlovedTracker:
    """Reuse the uploaded ArUco/HSV/contour pipeline with the shared engine."""
    def __init__(self):
        self.marker = Marker()
        self.roi = ROI(2.5, 2.5, 6, 0.45, 0.6, 0.4)
        self.glove = Glove()
        self.tracker = Tracker()
        self.last_tracker_init = 0

    def process(self, frame):
        from .recognition import Gest
        GestureController.cam_height, GestureController.cam_width = frame.shape[:2]
        self.marker.detect(frame)
        if self.marker.is_detected():
            if time.time() - self.last_tracker_init > 0.5:
                self.tracker.corners_to_tracker(self.marker.corners)
                self.tracker.tracker_started = False
                self.tracker.tracker = None
                self.tracker.CSRT_tracker(frame)
                self.last_tracker_init = time.time()
        else:
            self.tracker.CSRT_tracker(frame)
            if self.tracker.tracker_started:
                self.marker.corners = self.tracker.tracker_to_corner(None)
        if not self.marker.is_detected():
            return None, None
        try:
            self.roi.findROI(frame, self.marker)
            self.roi.find_glove_hsv(frame, self.marker)
            mask = self.roi.cropROI(frame)
            self.glove.find_fingers(mask)
            self.glove.find_gesture(frame)
            self.marker.draw_marker(frame)
            draw_box(frame, self.roi.roi_corners)
            point = (self.roi.marker_top[0]/frame.shape[1], self.roi.marker_top[1]/frame.shape[0])
            if self.glove.fingers == 0:
                return None, None
            # Preserve the glove variant's original move / double-click mapping.
            gesture = {3: Gest.V_GEST, 0: Gest.TWO_FINGER_CLOSED}.get(self.glove.gesture, Gest.UNKNOWN)
            return gesture, point
        except (ValueError, cv2.error, ZeroDivisionError):
            return None, None

    def close(self):
        self.tracker.tracker = None


if __name__ == "__main__":
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from src.app import main
    main()
