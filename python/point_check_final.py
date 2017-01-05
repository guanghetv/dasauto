# encoding: utf-8
'''
Created on 2016年12月31日
埋点测试基于python的最终版本
节约埋点测试的整体时间，尤其是小版本迭代，提高测试灵活性
埋点测试自动化的核心不在于操作本身的自动化，而在于数据测试的自动化
牺牲流程操作的自动化，换取更高效的数据测试，是可取的
WEB展示会是本版数据测试自动化的最终形态
@author: wangguojie
'''
import os,sys,re
from time import sleep
from collections import defaultdict,OrderedDict
from pymongo import MongoClient
import datetime
import copy
"""
 正确/错误/没发/多发/重发
"""
eventKey_item_status = defaultdict(lambda : defaultdict(list))
item_eventKey_correction_set = defaultdict(set)

device = None
test_tree_file = None
test_result_file = None

event = MongoClient(host = '10.8.8.111',
                    port = 27017, 
                    connect=False)['koala_dev']['eventv4']

# eventTime 用于筛选最近发送的埋点
# 考虑重复发送埋点的情况
def get_events(node, cur_time, item):
    global device,eventKey_item_status
    events = {}
    cursor = event.find({"serverTime":{"$gte":cur_time},"device":device})
    for dat in cursor:
        event_key = dat['eventKey']
        if not event_key in events:
            events.update({event_key: dat})
        else:
            eventKey_item_status[event_key][item].append("重复发送/"+node[0])
    return events

def same_list(list_a, list_b):
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
def same_point(dict_a, dict_b):
    if type(dict_b) == unicode:
        dict_b = dict_b.encode('utf-8')
    
    if type(dict_a) == type(dict_b):
        if type(dict_a) == dict:
            for k in dict_a:
                if not ( k in dict_b and same_point(dict_a[k], dict_b[k])) :
                    return False
        ## 考虑数组的情况
        ## 考虑特殊字段,只能考察key,value无法考察的情况
        elif type(dict_a) == list:
            if not same_list(dict_a, dict_b):
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

def get_diff(dict_a, dict_b):
    diff = {}
    if type(dict_a) == dict and type(dict_a) == type(dict_b):
        for k in dict_a:
            if not ( k in dict_b and same_point(dict_a[k], dict_b[k])) :
                if k in dict_b:
                    diff.update({k:(dict_a[k],dict_b[k])})
                else:
                    diff.update({k:(dict_a[k],'noKey')})
    return diff
            
def check(node,cur_time, item):
    events = get_events(node, cur_time, item)
    point_schema = node[1]
    for point in point_schema:
        if point in events:
            if point in point_schema and same_point(point_schema[point], events[point]) :
                item_eventKey_correction_set[item].update([point])
            else:
                eventKey_item_status[point][item].append("错误/"+node[0] +  "\t" + str(get_diff(point_schema[point], events[point])) + " id:" + str(events[point]['_id']))
        else:
            eventKey_item_status[point][item].append("没发/" + node[0])
        events.pop(point, None)
    
    for event in events:
        eventKey_item_status[event][item].append("多发/" + node[0])

def atom_point_test(node, item):
    global eventKey_item_status, item_eventKey_correction_set
    try:
        ## 存储埋点服务器的当前时间
        cur_time = datetime.datetime.now() - datetime.timedelta(hours=8)
        print("正在进行的操作是:    " + node[0])
        os.system('say ' + node[0].split('->')[-1])
        sleep(5)
        if len(node) > 1:
            check(node, cur_time, item)
    except:
        raise

def out():
    global eventKey_item_status,test_result_file,item_eventKey_correction_set
    with open(test_result_file, 'w') as result:
        for event_key in eventKey_item_status:
            result.write(event_key + '\n')
            for item in eventKey_item_status[event_key]:
                for status in eventKey_item_status[event_key][item]:
                    result.write("\t\t" + status + "\n")
            result.write('\n')
        result.write("本次测试正确的埋点:" + '\n')
        keys = set([])
        for item in item_eventKey_correction_set:
            for event_key in item_eventKey_correction_set[item]:
                if not event_key in eventKey_item_status:
                    keys.update([event_key])
        for key in keys:
            result.write(key + '\n')
def point_check():
    global test_tree_file,test_result_file
    item_diagram  = defaultdict(list)
    item_name = OrderedDict()
    with open(test_tree_file) as point_test_tree:
        next(point_test_tree, None)
        try:
            for dat in point_test_tree:
                dat = dat.strip("\n").strip('\t')
                if re.search('^[1-9]', dat) or re.search('^\\[', dat):
                    if re.search('^[1-9]', dat):
                        aid = dat[0:dat.index(" ")]
                        try:
                            aid = int(aid)
                        except:
                            pass
                        action = dat[dat.index(" "):].strip(' ')
                        if type(aid) == int:
                            item_name.update({aid:action})
                        else:
                            item_diagram[len(item_name)].append([action])
                    else:
                        item_diagram[len(item_name)][-1].append(eval(dat))
        except:
            raise
    
    item = 1
    while True:
        ## 输出可选项
        print("项目列表:")
        info = ''
        ## print(dict(item_name).decode('utf-8'))
        for item_t in item_name:
            info += str(item_t) + ":" + item_name[item_t] + ' '
        print(info)
        print('')
        os.system('say 请选择测试编号,并按回车键继续')
        key_input = raw_input("可选编号/q键退出,默认是 "+item_name[item] + ", 按 <ENTER> 键开始......    " )
        if key_input == "q":
            print("测试完毕,正保存测试结果......")
            os.system('say 测试完毕,正保存测试结果')
            out()
            break
        else:
            try:
                key_input = int(key_input)
            except:
                pass
            if type(key_input) == int:
                if key_input > len(item_diagram):
                    print("项目编号不存在,请重新选择")
                    os.system('say 项目编号不存在,请重新选择')
                    continue
                else:
                    if item != key_input:
                        item = key_input
                        print("将要测试的项目是:    " + item_name[item])
            else:
                if key_input != '':
                    print("项目编号不存在,请重新选择")
                    os.system('say 项目编号不存在,请重新选择')
                    continue

        ## 清除上次测试结果
        for key in eventKey_item_status:
            eventKey_item_status[key].pop(item, None)
        item_eventKey_correction_set.pop(item, None)
        actions = item_name[item]
        os.system('say 将要测试的项目是 ' + item_name[item])
        for e in item_diagram[item]:
            actions = actions + '->' + e[0]
            node = copy.deepcopy(e[1])
            point_schema = {}
            # 支持只有操作，不测埋点的情况，主要针对于重复测试的情况
            if len(node) > 0:
                for ele in node[0]:
                    point_schema.update({ele['eventKey'] : ele})
            node.insert(0, actions)
            if len(node) > 1:
                node[1] = point_schema
            atom_point_test(node, item)
        ## 输出结果,打印到屏幕
        points = set([])
        print("-----------------------------------------------------------------")
        for event_key in eventKey_item_status:
            if item in eventKey_item_status[event_key]:
                points.update([event_key])
                print(event_key + ":")
                for status in eventKey_item_status[event_key][item]:
                    print("\t\t" + status)
                print('')
        print("本次测试正确的埋点:")
        if item in item_eventKey_correction_set:
            for event_key in item_eventKey_correction_set[item]:
                if not event_key in points:
                    print(event_key)
        print("-----------------------------------------------------------------")
        print('')
        os.system('say 测试完毕,正保存测试结果')
        out()
        if item < len(item_diagram):
            item += 1


## python3 **.python device test_tree_file
if __name__ == '__main__': 
    if len(sys.argv) > 2: 
        test_tree_file = sys.argv[2]
        device = sys.argv[1]
        test_result_file = test_tree_file.replace("tree", "result")
        if len(sys.argv) > 3:
            test_result_file = sys.argv[3]
        point_check()
    else:
        print("脚本启动失败 此脚本至少需要device和test_tree_file两个变量")