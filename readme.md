[English Version](#english-version)

不支持除了GET以外的方法使用多线程下载  
不推荐用于日常浏览器使用, 有些功能可能不支持  
它不是那么稳定, 可能会导致一些东西失效, 莫名其妙404, 500, SSL Handshake Error等错误等, 所以如果出事了, 先把这个关掉  

通过 --with-cache 参数开启缓存, 默认会对一些特定文件上24小时缓存, 详情见configs.py  
通过 --with-history 参数开启历史记录, 它会记录流量, 然后默认在关闭时dump到/log  
通过 --gradle 参数为gradle开启代理, 详细配置见configs.py  
通过 --socks5 参数开启socks5代理  
通过 --print-env 参数来打印关于代理的环境变量  

参考init.py来导入ca证书  
注意, ca证书导入是可选项, 当且仅当你想要它作为系统代理的时候才需要使用, 而且它比较危险, 建议使用过后删除  

## gradle (java) 证书导入

cacerts是你从你的java home/lib/security目录下找到的证书文件，truststore.jks是你自己创建的信任库文件, 给gradle用的  
记得用gradle对应的java home  
记得重启你的IDE  
如果不是gralde, 你可能需要手动把信任库文件放回对应目录

```bash
keytool -importcert -alias do_not_trust_multithread_downloading_proxy_ca -file ca_server.crt -keystore truststore.jks -storepass changeit -noprompt
keytool -importkeystore -srckeystore cacerts -destkeystore truststore.jks -srcstorepass changeit -deststorepass changeit -noprompt
```

## 手动文件缓存

你可以手动指定直接从缓存返回的文件, 配置文件保存在configs.py指定的MFC_CONFIG_FILE里, 例子如下:

```yaml
- url: https://example.com/file.zip # 对这个url跳过缓存(严格匹配), 优先级最高
  cache: false
- url: https://example.com/file2.zip # 对这个url使用指定缓存路径
  cache: /path/to/cache/file2.zip
```

## 相关推荐工具
[netch](https://github.com/netchx/netch) 强制为特定软件使用socks5代理  
[dn](https://github.com/franticxx/dn) 多线程下载器(建议大于等于0.1.4版本)  

## 闲话  
是的这个没有英语版本.  
我在B站的视频可能被米哈游的一些开发或者什么人看到了, 所以启动器加了一点逻辑来限制证书来源, 杜绝中间人攻击  
这没什么不好的, 确实中间人攻击该防, 他们做的没啥问题, 但是至少这个项目的最初目标没有了  
我大概是不想维护了, 毕竟这个也写得比较完善了()  
(你写这么大一段就是为了说明自己要摆烂是吧)

<a id="english-version"></a>
## English Version

The multi-thread downloading proxy only supports GET method. Other HTTP methods are not supported.  
Not recommended for daily browser use as some features may not work properly.  
It's quite unstable and may cause failures, random 404/500 errors, SSL handshake errors, etc. If any issue occurs, disable it immediately.  

Cache can be enabled with --with-cache parameter. By default it sets 24-hour cache for certain files, see configs.py for details.  
History can be enabled with --with-history parameter. It records traffic and dumps it to /log when closed.  
Gradle proxying can be enabled with --gradle parameter. See configs.py for details of configuration.  
Socks5 proxying can be enabled with --socks5 parameter.  
Print environment variables about proxying with --print-env parameter.

Refer to init.py to import CA certificates.  
Note: CA certificate import is optional and only required when using as system proxy. It's potentially dangerous - recommended to remove after use.  

## Gradle (Java) Certificate Import

cacerts is the certificate file from your java home/lib/security directory. truststore.jks is the truststore file you created for gradle.  
Make sure to use the java home corresponding to your gradle installation.  
Don't forget to restart your IDE after configuration.  
If you are not using gradle, you may need to manually copy the truststore file back to the corresponding directory.

```bash
keytool -importcert -alias do_not_trust_multithread_downloading_proxy_ca -file ca_server.crt -keystore truststore.jks -storepass changeit -noprompt
keytool -importkeystore -srckeystore cacerts -destkeystore truststore.jks -srcstorepass changeit -deststorepass changeit -noprompt
```

## Manual file cache

You can specify files to be returned directly from cache, configuration is stored in MFC_CONFIG_FILE specified in configs.py, for example:

```yaml
- url: https://example.com/file.zip # Skip cache for this url (strict match), highest priority
  cache: false
- url: https://example.com/file2.zip # Use specified cache path for this url
  cache: /path/to/cache/file2.zip
```

## Recommanded Related tools
[netch](https://github.com/netchx/netch) Force proxy for specific software  
[dn](https://github.com/franticxx/dn) Multi-thread downloading tool (version >= 0.1.4 is recommended)  
