from platform import java_ver
from unittest import runner
from xml.etree.ElementTree import tostring
import cv2 as cv

import numpy as np
import os
import pytesseract
import matplotlib.pyplot as plt
import time
import tkinter

from PIL import ImageGrab
from asyncio.windows_events import NULL
from hashlib import new
from overlay import Overlay
from capture import Capture
from ocr import Tesseract_Ocr
import translate
#--------------------------------------------------------------------

os.chdir(os.path.dirname(os.path.abspath(__file__)))

Capture.list_window_names()
window_name=input()

caps = Capture(window_name)
ocrs = Tesseract_Ocr()

looptime = time.time()

#------------------------------variable------------------------------

#--------------------------------------------------------------------
#--------------------------------------------------------------------

def button1_pressed():
    if 'overlay_screen' in globals():
        overlay_screen.stop()
        del overlay_screen
    else:
        overlay_screen = Overlay(frame1)

#--------------------------------------------------------------------

#--------------------------------------------------------------------

def while_loop():
    #global overlay_screen_2
    #global overlay_screen_1
    #global overlay_switch
    overlay_screen_1 = Overlay(frame1)
    #overlay_screen_2 = Overlay(frame2)
    screenshot = caps.get_screenshot()
    result = ocrs.Get_Ocr_Tesseract(screenshot)
    for i in range(1, len(result["text"])):
        w = result["width"][i]
        h = result["height"][i]
        text = result["text"][i]
        conf = int(result["conf"][i])
    
        # while y++, until another cracter is come
        if(conf>70):
            tmptext = "".join([c if ord(c)<128 else "" for c in text]).strip()
            realtext = translate.GetTranslate(tmptext, 'en', 'ko')
            overlay_screen_1.labeler(realtext,result["left"][i],result["top"][i])
            #overlay_screen_2.labeler(tmptext,result["left"][i],result["top"][i])
            #tmptext = NULL
            #tmptext = Translate.Trans(tmptext, eng, kor)
    """"
    if(overlay_switch == True):
        overlay_screen_1.stop()
        print("overlay_1")
    else:
        overlay_screen_2.stop()
        print("overlay_2")
    overlay_switch = not overlay_switch
    """
    frame1.after(1000,while_loop)
    


#--------------------------------------------------------------------




frame1 = tkinter.Tk()
#frame2 = tkinter.Tk()
#global overlay_screen_1
overlay_screen_1 = Overlay(frame1)
#global overlay_screen_2
#overlay_screen_2 = Overlay(frame2)
#global overlay_switch
#overlay_switch = False
#button1 = tkinter.Button(frame1, text = 'Start OCR', background='white')
#button1.pack()
#button1.config(command=button1_pressed)
frame1.after(1000,while_loop)
frame1.mainloop()



    