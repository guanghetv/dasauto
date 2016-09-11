# encoding: utf-8
'''
Created on 2016年8月26日

@author: wangguojie
'''
import os
import re
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


"""
 正确/错误/没发/多发/重发
"""
eventKey_test_status = defaultdict(list)



test_tree_file = None
point_set = set([])

event = MongoClient(host = config.get('database', 'host'),
                            port = config.getint('database', 'port'), 
                            connect=False) \
                            [config.get('database', 'db')] \
                            [config.get('database', 'collection')]

deviceId = config.get('device', 'id')

# eventTime 用于筛选最近发送的埋点
# 考虑重复发送埋点的情况
def get_events(node, curTime):
    events = {}
    cursor = event.find({"eventTime":{"$gte":curTime},"device":deviceId})
    for dat in cursor:
        eventKey = dat['eventKey']
        if not eventKey in events:
            events.update({eventKey: dat})
        else:
            eventKey_test_status[eventKey].append("重复发送/"+node[0])
    return events


def sameList(list_a, list_b):
    if type(list_a) == list and type(list_b) == list:
        for ele in list_a:
            if ele in list_b:
                list_b.pop(list_b.index(ele))
            else:
                return False
        if len(list_b) != 0:
            return False
    else:
        return False
    return True

# dict_a字典每一个key对应的value应与dict_b[key]相同
def samePoint(dict_a, dict_b):
    if type(dict_b) == unicode:
        dict_b = dict_b.encode('utf-8')
    
    if type(dict_a) == type(dict_b):
        if type(dict_a) == dict:
            for k in dict_a:
                if not ( k in dict_b and samePoint(dict_a[k], dict_b[k])) :
                    return False
        ## 考虑数组的情况
        ## 考虑特殊字段,只能考察key,value无法考察的情况
        elif type(dict_a) == list:
            if not sameList(dict_a, dict_b):
                return False
        elif dict_a != dict_b:
            if (dict_a == "String" and type(dict_b) != str) \
                or (dict_a == "Number" and type(dict_b) != int and type(dict_b) != float) \
                or (dict_a == "Bool" and type(dict_b) != bool) \
                or (dict_a == "Array" and type(dict_b) != list) \
                or (dict_a != "onlykey" and dict_a != "String" and dict_a != "Number" and dict_a != "Bool" and dict_a != "Array"):
                return False
            
    else:
        if (dict_a == "String" and type(dict_b) != str) \
            or (dict_a == "Number" and type(dict_b) != int and type(dict_b) != float) \
            or (dict_a == "Bool" and type(dict_b) != bool) \
            or (dict_a == "Array" and type(dict_b) != list) \
            or (dict_a != "onlykey" and dict_a != "String" and dict_a != "Number" and dict_a != "Bool" and dict_a != "Array"):
            
            return False
        
    return True

def getDiff(dict_a, dict_b):
    keys = []
    if type(dict_a) == dict and type(dict_a) == type(dict_b):
        for k in dict_a:
            if not ( k in dict_b and samePoint(dict_a[k], dict_b[k])) :
                keys.append(k)
    return keys

class PonitTest(unittest.TestCase):
    def setUp(self):
        desired_caps = {}
        self.driver = webdriver.Remote('http://localhost:4723/wd/hub', desired_caps)
        self.driver.implicitly_wait(30)
        sleep(10)
        
    def tearDown(self):
        pass
        # end the session
#         self.driver.quit()
        

    def translate(self, node):
        print("正在进行的操作是:    " + node[0])
        for action in node[1]:
            if re.search('^os:', action):
                exec(action[action.index('os:') + 3: ])
            else:
                exec("self.driver." + action)
            sleep(0.5)
     
    def check(self, node,curTime):
        events = get_events(node, curTime)
        point_schema = node[2]
        for point in point_schema:
            if point in events:
                if point in point_schema and samePoint(point_schema[point], events[point]) :
                        pass
#                     eventKey_test_status[point].append("正确/" + node[0])
                else:
                    eventKey_test_status[point].append("错误/"+node[0] +  "\t" + str(getDiff(point_schema[point], events[point])) + "\tSchema:" +  str(point_schema[point]) + "\tEvent:" + str(events[point]))
            else:
                eventKey_test_status[point].append("没发/" + node[0])
            events.pop(point, None)
        
        for event in events:
            eventKey_test_status[event].append("多发/" + node[0])
     
    def atom_point_test(self, node):
        try:
            curTime = mktime(datetime.strptime(self.driver.device_time, "%a %b %d %H:%M:%S %Z %Y").timetuple())*1000
            
            self.translate(node)
            sleep(2)
            if len(node) > 2:
                self.check(node, curTime)
        except:
            print("error at line=" + str(getframeinfo(currentframe()).lineno) , sys.exc_info())
            raise
    
    def test_point(self):
        global point_set
        id_action = {}
        with open(test_tree_file) as point_test_tree:
            next(point_test_tree, None)
            try:
                action = None
                for dat in point_test_tree:
                    dat = dat.strip("\n").strip('\t')
                    if re.search('^[1-9]', dat) or re.search('^\\[', dat):
                        if re.search('^[1-9]', dat):
                            aid = dat[0:dat.index(" ")]
                            id_action.update({aid : dat[dat.index(" "):]})
                            action = dat[dat.index(" "):]
                            while aid.rfind('.') != -1:
                                aid = aid[0:aid.rfind('.')]
                                action = id_action[aid] + "->" + action
                        else:
                            node = eval(dat)
                            
                            point_schema = {}
                            # 支持只有操作，不测埋点的情况，主要针对于重复测试的情况
                            if len(node) > 1:
                                for ele in node[1]:
                                    point_schema.update({ele['eventKey'] : ele})
                                    point_set.update([ele['eventKey']])
                            
                            node.insert(0, action)
                            
                            if len(node) > 2:
                                node[2] = point_schema
                        
                            self.atom_point_test(node)
                            self.driver.page_source
                            sleep(5)
            except:
                print("error at line=" + str(getframeinfo(currentframe()).lineno) , sys.exc_info())
                raise

def out(test_result_file):
    print("正在保存测试结果......")
    global point_set,eventKey_test_status
    with open(test_result_file, 'w') as result: 
        for eventKey in eventKey_test_status:
            result.write(eventKey +  '\n')
            for status in eventKey_test_status[eventKey]:
                result.write("\t\t" + status + "\n")
            result.write('\n')
        result.write("本次测试的埋点:" + '\n')
        for point in point_set:
            result.write(point + '\n')
         
if __name__ == '__main__': 
    
    global test_tree_file
        
    if len(sys.argv) > 1:
        test_tree_file = sys.argv[1]
                  
        suite = unittest.TestLoader().loadTestsFromTestCase(PonitTest)
        unittest.TextTestRunner(verbosity=2).run(suite)
        
        out(test_tree_file.replace("tree", "result"))
    else:
        print("脚本启动失败 此脚本至少需要一个参数")
