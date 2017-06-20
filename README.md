# dasauto
埋点自动化测试

主要针对【点击事件->发送埋点】类型的即时相应进行埋点格式/数据的测试.

对于每一个测试埋点，有五种结果:

   1,正确：埋点预期(schema)的key，实际返回(event)里都有，而且key对应的value一 致；
         当预期value为“onlykey”时，表示只测试key是否一致;
         当预期value为“String/Number/Array/Bool”时,表示还需要测试value数据类型一致。

   2,错误：预期的key,实际返回或没有，或对应的value不一致；
         日志中的Schema和Event即为预期与实际返回数据；
         当预期value为“onlykey”时，表示只测试key是否一致;
         当预期value为“String/Number/Array/Bool”时,表示还需要测试value数据类型一致。

   3,重发：对应埋点(eventKey)重复发送。

   4,多发：对应埋点(eventKey)不需要发，多余发送。

   5,没发：对应埋点(eventKey)缺失，没有发送。

测试需要的软件:Appium
推荐使用的插件: XMind
可能用到的在线格式转换:  http://codebeautify.org/jsonviewer#    
                     http://codebeautify.org/xmlviewer


准备工作：
   1，安装appium  https://bitbucket.org/appium/appium.app/downloads/
   2，安装XMind http://www.xmind.net/

测试方式：
   将手机连接上电脑
   1，通过Xmind写测试用例 --> 打开Appium服务 --> 启动脚本,等待操作完成，即可看到测试结果
     python脚本格式: python point_test_V2.py ../data/android_login_tree.txt
     android_login_tree.txt为待测试的用例，有XMind文本形式导出,point_test_V2.py只支持这种文本格式，point_test_V1.py支持百度脑图导出格式(不推荐).
     输出与输出用例同目录同名前缀，如android_login_result.txt

     此处应有页面展示 。。。。。。
 
   2，打开Appium服务 --> 启动测试脚本GUI(提供输入/输出和开始测试按钮) --> 操作洋葱数学App  --> 在需要测试的地方，输入测试用例 
                   --> 开始测试,即可在输出框看到结果.
     python脚本格式: python point_test_gui.py
     

     主要是针对不容易测试的局部埋点，测试起来更灵活，当然也可以把方式1的测试用例放入输入框。
     GUI需要优化，勉强能用。

     此处有页面展示 。。。。。。

测试用例格式：
  对于测试用例的每一步，格式如下:
    [[statement_1,statement_2,...],[{schema_1},{schema_2},...]]
     是一个list，第一项是action string，就是触发某个埋点需要的方法表达式，一般情况下，强力推荐一步操作一条语句;
                     大多数情况下，statement是Appium webDriver相关的查询控件的表达式(find),比如根据text/content-desc/resource-id查询控件，点击或输入等;
                     如果find相关的表达式满足不了测试，比如想调用系统相关的函数，需要前面"os:"标识,比如点击/滑动屏幕,延迟等；
                     部分方法可能需要android、ios区别对待.
                第二项是测试相关的schema(json格式),可以为空(无需发埋点)，也可以没有(无需测试,主要针对重复用例).
    比如登录按钮:
       [["find_element_by_xpath('//*[@text=\"登录\"]').click()"],[{"eventKey":"clickHomeToLogin"},  {"eventKey":"enterLoginPage"}]]
    比如返回能力页：
[["tap([(50,100)])"],[{"eventKey":"enterAbilityHome"}]]
    比如向下滑动:
[["swipe(600,600,600,300)"]]

