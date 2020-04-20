#!/usr/bin/env python3
import os.path
import os
import click
from opencc import OpenCC
from mutagen.flac import FLAC
from mutagen.easyid3 import EasyID3
from mutagen.mp4 import MP4
import http.client
import hashlib
import urllib
import random
import json
import time
import re
#注册百度开发者账号 https://api.fanyi.baidu.com/doc/12
appid = ''  # 填写你的appid
secretKey = ''  # 填写你的密钥

dir_list = []  #需要改名的文件夹list
file_list = [] #需要改名的文件list
cc = None   #如果是中文简繁转换就初始化cc，否则进行百度翻译

@click.command()
@click.option('-m','--music-dir','music_dir', prompt='音乐目录', help='音乐目录')
@click.option('-c','--clean-type','clean_type',default=1,
              help='清洗类型，默认为1。 0:强力清洗  1：基本清洗')
@click.option('-s','--src-language','src_language',
              default="cht",
              help='Tag原始语言，默认繁体中文。')
@click.option('-d','--dst-language','dst_language',
              default="zh",
              help='Tag目标语言，默认简体中文。')
def clean_audio_dir(music_dir, clean_type=1, src_language="cht", dst_language="chs"):
    """
    音乐文件Tag清洗程序。支持mp3,flac,m4a格式。中文简繁转换使用opencc库,其他语言转换走百度翻译。
    需要翻译的请注册个人开发者，申请app key 并填入变量中。 https://api.fanyi.baidu.com/doc/12 \n

    清洗类型，默认为1。
    0:只清洗并保留艺术家、标题、专辑、专辑艺术家、音轨号、光盘号，其余全部清除
    1:只对艺术家、标题、专辑、专辑艺术家进行清洗，其他Tag不处理\n
    语言支持：
    auto:自动检测、zh:中文、jp:日语、cht:繁体中文
    支持翻译语言类型请见百度翻译文档：https://api.fanyi.baidu.com/doc/21
    """
    global cc
    if src_language =="cht" and dst_language=="zh":
        cc = OpenCC('t2s')
    elif src_language =="zh" and dst_language=="cht":
        cc = OpenCC('s2t')


    for parent,dirnames,filenames in os.walk(music_dir):    #三个参数：分别返回1.父目录 2.所有文件夹名字（不含路径） 3.所有文件名字
        for dirname in  dirnames:                       #输出文件夹信息
            if cc is not None:
                dirname_converted = cc.convert(dirname)
            else:
                dirname_converted = translate(dirname,src_language,dst_language)
            cur_relative_dir = os.path.join(parent, dirname)
            cur_relative_dir_converted = os.path.join(parent,dirname_converted)

            dir_list.append([cur_relative_dir,cur_relative_dir_converted])


        for filename in filenames:  # 输出文件信息
            filename_without_suffix = os.path.splitext(filename)[0]
            file_suffix = os.path.splitext(filename)[-1]

            #文件名翻译和转换只转换文件名部分，排除文件后缀
            if cc is not None:
                filename_converted = cc.convert(filename_without_suffix)+file_suffix
            else: #百度翻译会把空格去掉，需要特殊处理,否则无法根据文件名提取出音轨号
                if re.search('^\d+-\d+',filename_without_suffix) is not None: #先判断是否是多个CD
                    tracker = re.search('^\d+-\d+',filename_without_suffix).group()
                    filename_tmp =  filename_without_suffix.replace(tracker,"")
                    filename_converted=  tracker +" "+ translate(filename_tmp,src_language,dst_language)+file_suffix
                elif re.search('^\d+',filename_without_suffix) is not None: #单CD
                    tracker = re.search('^\d+',filename_without_suffix).group()
                    filename_tmp =  filename_without_suffix.replace(tracker,"")
                    filename_converted=  tracker +" "+ translate(filename_tmp,src_language,dst_language)+file_suffix
                else:
                    filename_converted = translate(filename_without_suffix,src_language,dst_language)+file_suffix


            cur_relative_filename = os.path.join(parent, filename)
            cur_relative_filename_converted  = os.path.join(parent, filename_converted)
            file_list.append([cur_relative_filename,cur_relative_filename_converted])


            if  file_suffix in  [".flac",".FLAC"]:
                audio = FLAC(cur_relative_filename)
                print("开始修改 FLAC TAG：")
                print(audio)
                clean_mp3_flac_tags(audio, clean_type, src_language, dst_language)
            elif file_suffix in [".mp3",".MP3"]:
                audio = EasyID3(cur_relative_filename)
                print("开始修改 MP3 TAG：")
                print(audio)
                clean_mp3_flac_tags(audio, clean_type, src_language, dst_language)
            elif file_suffix in [".m4a",".m4b",".m4p",".M4A",".M4B",".M4P"]:
                audio =  MP4(cur_relative_filename)
                print("开始修改 MP4 TAG：")
                #print(audio)
                info = [audio["©nam"],audio["©ART"],audio["©alb"]]
                print(info)
                clean_mp4_tags(audio, clean_type, src_language, dst_language)




    print("-------------------------")
    print("开始修改文件名....")
    for item in file_list:
        print("---开始修改文件---")
        print(item[0])
        print(item[1])
        os.rename(item[0],item[1])

    #文件夹list倒序，先改最里面的目录
    dir_list.reverse()
    print("开始修改目录名....")
    for item in dir_list:
        print("开始修改 "+item[0])
        os.rename(item[0],item[1])


#获取MP3 FLAC TAG
def get_mp3_flac_basic_tags(audio):
    try:
        album = audio["album"][0]
    except:
        album = ""

    try:
        title = audio["title"][0]
    except:
        title = ""

    try:
        artist = audio["artist"][0]
    except:
        artist = ""

    try:
        albumartist = audio["albumartist"][0]
    except:
        albumartist = artist

    try:
        date = audio["date"][0]
    except:
        date = ""

    try:
        tracknumber = audio["tracknumber"][0]
    except:
        tracknumber = ""

    try:
        discnumber = audio["discnumber"][0]
    except:
        discnumber=""

    return album,title,artist,albumartist,date,tracknumber,discnumber


def get_mp4_basic_tags(audio):
    try:
        nam = audio["©nam"][0]
    except:
        nam=""

    try:
        ART = audio["©ART"][0]
    except:
        ART=""

    try:
        alb = audio["©alb"][0]
    except:
        alb=""

    try:
        wrt = audio["©wrt"][0]
    except:
        wrt=""

    try:
        trkn = audio["trkn"]
    except:
        trkn = ""

    try:
        disk = audio["disk"]
    except:
        disk = ""

    try:
        day = audio["©day"][0]
    except:
        day=""
    print("获取mp4 tag:")
    print([nam,ART,alb,wrt,trkn,disk,day])
    return  nam,ART,alb,wrt,trkn,disk,day

#将繁体中文tag转换成简体中文，并清空多余tag
#注意：mp3文件执行audio.delete()会把封面图也清空，flac则不清空封面图
def clean_mp3_flac_tags(audio, clean_type, src_language, dst_language):
    #print(audio)
    #tag 转换简体中文
    album,title,artist,albumartist,date,tracknumber,discnumber = get_mp3_flac_basic_tags(audio)
    if clean_type == 0:audio.delete()  #如果清理模式为0，则清空全部Tag,然后新增转换后的Tag，默认为1，不清空
    global cc
    if cc is not None:
        print("cc is not none")
        #Tag语言转换
        audio["album"] = cc.convert(album)
        audio["title"] = cc.convert(title)
        audio["artist"] = cc.convert(artist)
        audio["albumartist"] = cc.convert(albumartist)
        audio["date"] = date
        audio["tracknumber"] = tracknumber
        audio["discnumber"] = discnumber
        audio.save()
    else: #非中文则进行翻译
        if album !="" : album=translate(album,src_language,dst_language)
        if title !="" : title=translate(title,src_language,dst_language)
        if artist !="" : artist=translate(artist,src_language,dst_language)
        if albumartist !="" : albumartist=translate(albumartist,src_language,dst_language)

        audio["album"] =album
        audio["title"] = title
        audio["artist"] = artist
        audio["albumartist"] = albumartist
        audio["date"] = date
        audio["tracknumber"] = tracknumber
        audio["discnumber"] = discnumber
        audio.save()

    print("--修改后--")
    print(audio)


#This module will read MPEG-4 audio information and metadata, as found in Apple’s MP4 (aka M4A, M4B, M4P) files.
def clean_mp4_tags(audio, clean_type, src_language, dst_language):
    nam,ART,alb,wrt,trkn,disk,day = get_mp4_basic_tags(audio)
    if clean_type == 0:audio.delete()  #如果清理模式为0，则清空全部Tag,然后新增转换后的Tag，默认为1，不清空
    global cc
    if cc is not None:
        audio["©nam"] = cc.convert(nam)
        audio["©ART"] = cc.convert(ART)
        audio["©alb"] = cc.convert(alb)
        audio["©wrt"] = cc.convert(wrt)
        audio["trkn"] = trkn
        audio["disk"] = disk
        audio["©day"] = day
        audio.save()
    else: #非中文则进行翻译
        if nam != "" : nam=translate(nam,src_language,dst_language)
        if ART != "" : ART=translate(ART,src_language,dst_language)
        if alb != "" : alb=translate(alb,src_language,dst_language)
        if wrt != "" : wrt=translate(wrt,src_language,dst_language)

        audio["©nam"] = nam
        audio["©ART"] = ART
        audio["©alb"] = alb
        audio["©wrt"] = wrt
        audio["trkn"] = trkn
        audio["disk"] = disk
        audio["©day"] = day
        audio.save()

    print("--修改后--")
    print([audio["©nam"],audio["©ART"],audio["©alb"],audio["©wrt"] ])


#调用百度翻译
def translate(q,src_code,dst_code):
    httpClient = None
    myurl = '/api/trans/vip/translate'

    fromLang = src_code   #原文语种
    toLang = dst_code   #译文语种
    salt = random.randint(32768, 65536)
    sign = appid + q + str(salt) + secretKey
    sign = hashlib.md5(sign.encode()).hexdigest()
    myurl = myurl + '?appid=' + appid + '&q=' + urllib.parse.quote(q) + '&from=' + fromLang + '&to=' + toLang + '&salt=' + str(
        salt) + '&sign=' + sign

    dst = None
    print("-------开始百度翻译-------")
    print([src_code,dst_code])
    print(q)
    try:
        httpClient = http.client.HTTPConnection('api.fanyi.baidu.com')
        httpClient.request('GET', myurl)
        # response是HTTPResponse对象
        response = httpClient.getresponse()
        result_all = response.read().decode("utf-8")
        result = json.loads(result_all)
        #print (result)
        dst = result["trans_result"][0]["dst"]
        if src_code == "jp":
            dst = dst.replace("。","")  #日语翻译经常出现句号，清空掉
    except Exception as e:
        print (e)
    finally:
        if httpClient:
            httpClient.close()

    print(dst)
    print("-------结束百度翻译-------")
    return  dst


if __name__ == '__main__':
    clean_audio_dir()