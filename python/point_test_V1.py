# encoding: utf-8
'''
Created on 2016年8月18日
Android 埋点测试自动化
@author: wangguojie
'''
import os
import sys
import unittest
from time import sleep, mktime
from appium import webdriver
from inspect import getframeinfo, currentframe
from collections import defaultdict
from pymongo import MongoClient
from datetime import datetime

import ConfigParser


#加载配置文件
config = ConfigParser.ConfigParser()
config.read(os.path.abspath(os.path.join(os.path.abspath(__file__),
                                                            os.pardir, os.pardir
                                                            , 'data', 'point_test.cfg')))


# 有实际内容，除了检查字段，也检查字段对应的信息
eventKey_schema = defaultdict(dict)

# 1 ： 正确
# 0 ： 错误
# -1 ：没发
# -2 ：多发
# -3 ：重发
eventKey_test_status = defaultdict(list)

test_tree_file = None

event = MongoClient(host = config.get('database', 'host'),
                            port = config.getint('database', 'port'), 
                            connect=False) \
                            [config.get('database', 'db')] \
                            [config.get('database', 'collection')]


# eventTime 用于筛选最近发送的埋点
# 考虑重复发送埋点的情况
def get_events(actions, points, eventTime):
    events = {}
    cursor = event.find({"eventTime":{"$gte":eventTime}})
    for dat in cursor:
        eventKey = dat['eventKey']
        if not eventKey in events:
            events.update({eventKey: dat})
        else:
            eventKey_test_status[eventKey].append([actions, points, -3])
    return events

# dict_a字典每一个key对应的value应与dict_b[key]相同
def samePoint(dict_a, dict_b):
    if type(dict_b) == unicode:
        dict_b = dict_b.encode('utf-8')
    
    if type(dict_a) == type(dict_b):
        if type(dict_a) == dict:
            for k in dict_a:
                if not ( k in dict_b and samePoint(dict_a[k], dict_b[k])) :
                    return False
        elif dict_a != dict_b:
            return False
    else:
        return False
    return True


class PonitTest(unittest.TestCase):
    def setUp(self):
        desired_caps = {}
        self.driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
        self.driver.implicitly_wait(10)
        
    def tearDown(self):
        # end the session
        self.driver.quit()
        

    def translate(self, actions):
        print "马上进行的操作是 ", actions
        print
        
        for action in actions:
            print action
            exec("self.driver." + action)
            sleep(0.5)
     
    def check(self, actions, points, eventTime):
        events = get_events(actions, points, eventTime)
        for point in points:        
            if point in events:
                if samePoint(eventKey_schema[point], events[point]) :
                    eventKey_test_status[point].append([actions, point ,1])
                else:
                    eventKey_test_status[point].append([actions, point ,0])
            else:
                eventKey_test_status[point].append([actions, point ,-1])
            events.pop(point, None)
        
        for event in events:
            eventKey_test_status[event].append([actions, points , -2])
     
    def atom_point_test(self,node):
        print "下一个事件是 ", node[0].decode('utf-8')
        try:
            actions = node[1]
            
            points = []
            if len(node) > 2:
                points = node[2]
             
            eventTime = mktime(datetime.strptime(self.driver.device_time, "%a %b %d %H:%M:%S %Z %Y").timetuple())*1000
             
            self.translate(actions)
            sleep(2)
            self.check(actions, points, eventTime)
        except:
            print("error at line=" + str(getframeinfo(currentframe()).lineno) , sys.exc_info())
            raise
         
    def test_point(self):
        with open(test_tree_file) as point_test_tree:
            next(point_test_tree, None)
            try:
                for node in point_test_tree:
                    node = node.strip("\n").strip('\t')
                    self.atom_point_test(eval(node))
                    sleep(5)

            except:
                print("error at line=" + str(getframeinfo(currentframe()).lineno) , sys.exc_info())
                raise


# 加载埋点schema,需提供实际value
def load_point_schema(point_schema_file):
    with open(point_schema_file) as point_test_schema:
        next(point_test_schema, None)
        for dat in point_test_schema:
            dat = dat.strip('\n').split('\t')
            eventKey_schema[dat[0]] = eval(dat[1])

def out(test_result_file):
    print("正在保存测试结果......")
    with open(test_result_file, 'w') as result: 
        for eventKey in eventKey_test_status:
            result.write("\t".join([eventKey, str(eventKey_test_status[eventKey])]))
            result.write('\n')
         
if __name__ == '__main__': 
    
    global test_tree_file
        
    if len(sys.argv) > 2:
        test_tree_file = sys.argv[1]
        point_schema_file = sys.argv[2]
         
        load_point_schema(point_schema_file)
         
        suite = unittest.TestLoader().loadTestsFromTestCase(PonitTest)
        unittest.TextTestRunner(verbosity=2).run(suite)
        
        out(test_tree_file.replace("tree", "result"))
    else:
        print("脚本启动失败 此脚本至少需要两个参数")
