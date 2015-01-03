# -*- coding: cp936 -*-
import ctypes
from ctypes import *
import re,json
from PIL import Image
import os

class CarRecgEngine:
    def __init__(self):
        #��������ʶ������
        self.dll = ctypes.cdll.LoadLibrary( 'CarRecogniseEngine.dll' )
        self.engineID = self.dll.InitialEngine()
        #����ͼƬ��ȡ�ļ���
        self.file = 'cropimg'
        if os.path.exists(self.file) == False:
            os.makedirs(self.file)

    #ʶ������Ϣ
    def imgrecg(self,path,coordinates=None):
        try:
            recg_path = None
            if coordinates != None:
                path = self.crop_img(path,coordinates)
                recg_path = path
                
            pStrUrl = create_string_buffer(path)
            szResult = create_string_buffer('\0'*1024)

            ret = self.dll.doRecg( self.engineID, byref(pStrUrl),byref(szResult), 1024);

            return self.rematch(szResult.value)
        except Exception,e:
            return None
        finally:
            try:
                if recg_path != None:
                    os.remove(recg_path)
            except Exception,e:
                pass
        

    def uninit(self):
        self.dll.UnInitialEngine(self.engineID)

    #ת����׼Json��ʽ
    def rematch(self,j):
        j = re.sub(r"{\s*(\w)",r'{"\1',j)
        j = re.sub(r",\s*(\w)",r',"\1',j)
        j = re.sub(r"(\D):",r'\1":',j)
        j = j.replace("'", "\"")

        return json.loads(j,'gbk')

    #ͼƬ��ȡ
    def crop_img(self,path,coordinates):
        im = Image.open(path)

        box = (coordinates[0], coordinates[1], coordinates[2], coordinates[3])
        region = im.crop(box)
        
        filename = os.path.basename(path)

        crop_path = os.path.join(self.file,filename)
        region.save(crop_path)
        
        return crop_path


if __name__ == '__main__':
    cr = CarRecgEngine()
    area1 = (0,357,1316,2046)
    area2 = (0,357,2398,1779)
    a=cr.imgrecg('img/15023100073.jpg',area1)
    #a = '{"head":{"code":1,"count":0,"msg":"ʶ��ɹ�"},"body":"[{"ywcl":1,"ywhp":1,"hpzl":"02","hphm":"��LXA293","cllx":"K33","csys":"J","ppdm":"012","clpp":"���ǵ�F3","kxd": 69,"jcsj":"2014-10-28 23":51":17"}]"}'
    #b = '{"head":{"code":1,"count":0,"msg":"ʶ��ɹ�"},"body":"123"}'
    #print a[]
    #b = cr.imgrecg(a)
    print a
    #print b['body']
    #cr.uninit()
    del cr
    #print os.path.exists('img3')
    #print os.path.join('img','123.jpg')








    
