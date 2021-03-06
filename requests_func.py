# -*- coding: utf-8 -*-
import shutil

import requests


class RequestsFunc:
    """HTTP客服端类"""
    def get_url_img(self, url, path):
        """根据URL地址抓图到本地文件"""
        r = requests.get(url, stream=True)

        if r.status_code == 200:
            with open(path, 'wb') as f:
                r.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
        # 非200响应,抛出异常
        r.raise_for_status()

    def send_post(self, url, send_data):
        """POST请求"""
        r = requests.post(url, data=send_data,headers={'content-type':'application/json'})

        return r.text

if __name__ == '__main__':
    import json
    url = 'http://localhost:8060/recg'
    json_data = {'imgurl':'http://localhost/imgareaselect/imgs/1.jpg','coordinates':None}
    rf = RequestsFunc()
    data={'key':'sx2767722_10','info': json_data}
    print rf.send_post(url,json.dumps(data))

    del rf
    #rf.get_url_img(url,'c:/imgdownload/test2.jpg')
    #print rf.send_post(url, data)
