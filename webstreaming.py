# import the necessary packages
pip install Flask
pip install opencv-python
pip install imutils

# import the necessary packages
from pyimagesearch.motion_detection.SingleMotionDetector import * 
from imutils.video import VideoStream# 将允许我们访问我们的Raspberry Pi 相机模块或 USB网络摄像头.
from flask import Response#第4到6行处理导入我们需要的Flask包——我们将使用这些包呈现我们的index.html模板，并将其提供给客户端
from flask import Flask
from flask import render_template
import threading#第7行导入threading库，确保我们可以支持并发 (比如，同时使用多个客户端、网络浏览器和选项卡)。
import argparse
import datetime
import imutils
import time
import cv2

# initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
outputFrame = None#这将是将提供给客户端的帧(投递运动检测)。
lock = threading.Lock()#它将在更新ouputFrame时被用来确保线程安全行为(即确保某个帧在更新时不被任何线程尝试读取）。

# initialize a flask object
app = Flask(__name__)#初始化我们的Flask  app本身，

# initialize the video stream and allow the camera sensor to
# warmup
#vs = VideoStream(usePiCamera=1).start()#行访问我们的视频流:
vs = VideoStream(src=0).start()#如果您正在使用一个USB网络摄像头, 您可以保持代码不变。
time.sleep(2.0)#否则,如果您正在使用一个RPi相机模块，那您应该取消掉第25行的注释，并将第26行注释掉。 

@app.route("/")#下一个函数index将会渲染我们的index.html模板并提供输出视频流:
#装饰器其实就是在一个函数内部定义另外一个函数,然后返回一个新的函数,即动态的给一个对象添加额外的职责
#
def index():#这个函数非常简单—它所做的就是在我们的HTML文件中调用Flask render_template。
    # return the rendered template
    return render_template("index.html")
#我们的下一个函数的功能是:#对我们视频流中的帧进行循环#应用运动检测#在outputFrame上绘制任何结果#而且，这个函数必须以线程安全的方式来执行所有这些操作，以确保支持并发。
def detect_motion(frameCount):#我们的detection_motion函数接受单个参数frameCount，它是在SingleMotionDetector类中构建我们的背景bg所需的最小帧数:
    # grab global references to the video stream, output frame, and#如果我们没有至少frameCount帧，我们将会继续计算累计加权平均值
    # lock variables#一旦frameCount达到了，我们将执行背景去除
    global vs, outputFrame, lock#vs: 我们实例化的VideoStream对象,outputFrame: 将提供给客户端的输出帧,lock: 在更新outputFrame之前我们必须获得的线程锁
    # initialize the motion detector and the total number of frames
    # read thus far
    md = SingleMotionDetector(accumWeight=0.1)#使用一个accumWeight=0.1值来初始化我们的SingleMotionDetector 类，这意味着在计算加权平均值时，bg值的权重会更高。
    total = 0#初始化到目前为止读取的帧的total数——我们需要确保已经读取了足够多的帧来构建我们的背景模型。
# loop over frames from the video stream
    while True:
        # read the next frame from the video stream, resize it,
        # convert the frame to grayscale, and blur it
        frame = vs.read()
        frame = imutils.resize(frame, width=400)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (7, 7), 0)
        # grab the current timestamp and draw it on the frame
        timestamp = datetime.datetime.now()#们获取当前时间戳并将其绘制在frame上(第54-57行)。
        cv2.putText(frame, timestamp.strftime(
			"%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
            cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 0, 255), 1)
        # if the total number of frames has reached a sufficient
        # number to construct a reasonable background model, then
        # continue to process the frame
        if total > frameCount:#我们确保我们至少读取了frameCount帧来构建我们的背景去除模型。
            # detect motion in the image
            motion = md.detect(gray)#应用我们运动检测器的.detect运动，它将返回单个变量motion。
            # check to see if motion was found in the frame
            if motion is not None:
                # unpack the tuple and draw the box surrounding the
                # "motion area" on the output frame
                (thresh, (minX, minY, maxX, maxY)) = motion
                cv2.rectangle(frame, (minX, minY), (maxX, maxY),
                              (0, 0, 255), 2)
		
        # update the background model and increment(增加) the total number
        # of frames read thus far
        md.update(gray)
        total += 1
        # acquire the lock, set the output frame, and release the
        # lock
        with lock:#第81行获得支持线程并发所需的lock，而第82行设置outputFrame。
            outputFrame = frame.copy()#我们需要获取锁，以确保我们在试图更新outputFrame变量时客户机不会意外读取它。
            
def generate():#是一个Python生成器，用于将我们的outputFrame编码为JPEG数据——现在让我们来看看它:
        # grab global references to the output frame and lock variables
        global outputFrame, lock#获取对outputFrame和lock的全局引用，类似于detect_motion函数。
        # loop over frames from the output stream
        while True:#获取对outputFrame和lock的全局引用，类似于detect_motion函数。
            # wait until the lock is acquired
            with lock:
                # check if the output frame is available, otherwise skip
                # the iteration of the loop
                if outputFrame is None:
                    continue
                # encode the frame in JPEG format
                (flag, encodedImage) = cv2.imencode(".jpg", outputFrame)
                # ensure the frame was successfully encoded
                if not flag:
                    continue
            # yield the output frame in the byte format
            yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + 
                  bytearray(encodedImage) + b'\r\n')
#函数video_feed会调用我们的generate函数:
            
######################这个app.route签名告诉Flask这个函数是一个URL端点，数据是从http://your_ip_address/video_feed提供的。
            #video_feed的输出是实时运动检测输出，通过generate函数编码为一个字节数组。您的网络浏览器非常聪明，可以将这个字节数组作为一个实时输出显示在您的浏览器中。
@app.route("/video_feed")
def video_feed():
        # return the response generated along with the specific media
        # type (mime type)
        return Response(generate(),
                        mimetype = "multipart/x-mixed-replace; boundary=frame")
# check to see if this is the main thread of execution
        #解析命令行参数和启动Flask应用程序的任务:
if __name__ == '__main__':
    # construct the argument parser and parse command line arguments
    #ap = argparse.ArgumentParser()
    #ap.add_argument("-i", "--ip", type=str, required=True,
    #                help="ip address of the device")#您运行webstream.py文件的系统的IP地址。
    #ap.add_argument("-o", "--port", type=int, required=True,# Flask应用程序的运行端口号(对这个参数，您通常只需要提供一个值8000）
    #                help="ephemeral port number of the server (1024 to 65535)")
    #ap.add_argument("-f", "--frame-count", type=int, default=32,#在执行运动检测之前用于累计和构建背景模型的帧数。默认情况下，我们使用32帧来构建背景模型。 
    #                help="# of frames used to construct the background model")
    #args = vars(ap.parse_args())#函数返回对象object的属性和属性值的字典对象
    args = {'ip':'192.168.3.3','port':8000,'frame_count':32}
    #启动一个线程用于执行运动检测。
    #使用一个线程确保detect_motion函数可以安全地在后台运行——它将不断地运行和更新我们的outputFrame，以便我们可以为我们的客户端提供任何运动检测结果
    # start a thread that will perform motion detection
    t = threading.Thread(target=detect_motion, args=(
        args["frame_count"],))
    t.daemon = True
    t.start()
    # start the flask app#134和135行启动Flask应用程序本身。
    app.run(host=args["ip"], port=args["port"], debug=True,
            threaded=True, use_reloader=False)
# release the video stream pointer
vs.stop()