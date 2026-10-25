"""Desktop language is independent from the camera's Chinese option."""
TEXT = {
    'title': ('Sony语言解锁', 'Sony Language Unlock'),
    'scope': ('适用：日版sony', 'For Japanese-market Sony cameras'),
    'detect': ('检测设备', 'Detect camera'),
    'device_none': ('设备：尚未检测', 'Camera: not detected'),
    'device_info': ('设备：{model}　固件：{version}', 'Camera: {model}   Firmware: {version}'),
    'support': ('当前写入支持：ILCE-7CM2 / 2.01 / J1；其他机型仅检测。', 'Writing currently supported: ILCE-7CM2 / 2.01 / J1. Other models: detection only.'),
    'chinese': ('解锁中文（简体＋繁体）', 'Unlock Chinese (Simplified + Traditional)'),
    'description_off': ('开启其他语言，关闭两项中文；不读取固件包或字体。', 'Enable other languages and disable both Chinese options. No firmware or font access.'),
    'description_on': ('开启全部语言，恢复保护后补齐中文字体和图标字体。请选择对应固件包。', 'Enable all languages, restore protection, then restore Chinese and icon fonts. Select a matching firmware package.'),
    'firmware_none': ('固件包：尚未选择', 'Firmware package: not selected'),
    'firmware_info': ('固件包：{model} / {version}', 'Firmware package: {model} / {version}'),
    'select': ('选择固件包…', 'Select firmware…'),
    'replace': ('更换固件包…', 'Replace firmware…'),
    'package_help': ('固件包只用于校验和提取字体，不会安装或升级相机固件。', 'The package is used to verify and extract fonts. It does not install or upgrade camera firmware.'),
    'connect_help': ('相机开机，USB 选择“大容量存储 / MSC”；两个相机接口均需 WinUSB，设置方法见 README。关闭其他相机工具。', 'Turn on the camera and select Mass Storage / MSC. Both camera interfaces require WinUSB; see README for setup. Close other camera tools.'),
    'start': ('开始解锁', 'Start unlock'),
    'records': ('打开本机记录', 'Open local records'),
    'restarted': ('我已断开 USB、重启并确认菜单正常，然后重新连接 MSC', 'I disconnected USB, restarted, checked the menus, and reconnected in MSC mode'),
    'verify': ('重启后只读核对', 'Read-only check after restart'),
    'persistence': ('固件升级后是否需要重复操作：尚未测试。', 'Persistence after firmware updates has not been tested.'),
    'notice': ('提示', 'Notice'),
    'stopped': ('操作已停止', 'Operation stopped'),
    'detect_first': ('请先检测设备。', 'Detect the camera first.'),
    'select_required': ('已选择解锁中文，请先选择固件包。', 'Chinese unlock is selected. Select a firmware package first.'),
    'version_mismatch': ('固件版本不一致：设备 {device}，固件包 {package}。请选择对应版本。', 'Firmware version mismatch: camera {device}, package {package}. Select a matching version.'),
    'model_mismatch': ('固件包型号与设备不一致：设备 {device}，固件包 {package}。', 'Model mismatch: camera {device}, package {package}.'),
    'unsupported': ('已检测到 {model} / {version}，此型号或版本尚未验证写入，已停止。', 'Detected {model} / {version}. Writing for this model or version has not been validated; stopped.'),
    'package_unverified': ('这个固件包尚未通过本项目验证，不能用于写入。', 'This firmware package has not been validated for writing by this project.'),
    'device_changed': ('设备或固件版本已改变，请重新检测。', 'The camera or firmware version changed. Detect the camera again.'),
    'package_changed': ('所选固件包已改变，请重新选择。', 'The selected firmware package changed. Select it again.'),
    'restart_first': ('请先手动重启并检查语言菜单，然后勾选确认项。', 'Restart manually, check the language menus, then tick the confirmation box.'),
    'await_restart': ('读回通过。请断开 USB、关机再开机并检查菜单，然后重新连接执行只读核对。', 'Read-back passed. Disconnect USB, power off and on, check the menus, then reconnect for the read-only check.'),
    'verified': ('语言设置、保护状态及所选资源核对通过。', 'Language settings, protection, and selected resources passed verification.'),
    'wait_close': ('正在执行，请等待操作结束。', 'An operation is running. Wait for it to finish.'),
    'detecting': ('正在检测设备和固件版本…', 'Detecting camera and firmware version…'),
    'service_detect': ('已识别 ILCE-7CM2，正在通过受保护的只读连接读取版本和机身身份…', 'ILCE-7CM2 detected. Reading version and body identity through the guarded read-only connection…'),
    'usb_reconnect': ('USB 通信在 {stage} 阶段中断。请停止重复检测，断开 USB、关机再开机，然后重新连接 MSC。详细阶段已保存到本机记录。', 'USB communication failed at {stage}. Stop repeated attempts, disconnect USB, power off and on, then reconnect in MSC mode. The stages were saved to local records.'),
    'reconnect_required': ('普通 USB 模式尚未恢复。请断开 USB、关机再开机，然后重新连接 MSC。', 'Normal USB mode has not returned. Disconnect USB, power off and on, then reconnect in MSC mode.'),
    'inspecting': ('正在检查所选固件包…', 'Checking the selected firmware package…'),
    'starting': ('正在重新核对设备并准备解锁…', 'Rechecking the camera and preparing to unlock…'),
    'no_camera': ('未找到 Sony MSC 相机，请连接并选择大容量存储。', 'No Sony MSC camera found. Connect it and select Mass Storage.'),
    'libusb1_missing': ('无法加载随包 USB 通信库，请完整解压发行包并保留 _internal 文件夹。', 'Cannot load the bundled USB library. Extract the complete release and keep the _internal folder.'),
    'multiple': ('请只连接一台 Sony 相机。', 'Connect only one Sony camera.'),
    'busy_timeout': ('设备响应超时，请检查相机连接状态后重新检测。', 'Camera response timed out. Check the connection and detect again.'),
    'invalid_package': ('无法读取有效的 Sony 固件包，请选择原始 BODYDATA.DAT。', 'Cannot read a valid Sony firmware package. Select the original BODYDATA.DAT.'),
    'invalid_version': ('未能读取有效的设备固件版本。', 'Could not read a valid camera firmware version.'),
    'technical': ('技术详情：{detail}', 'Technical details (original): {detail}'),
}


class UserError(ValueError):
    def __init__(self, key, **values):
        self.key, self.values = key, values
        super().__init__(translate(key, 'zh', **values))


def translate(key, language='zh', **values):
    return TEXT[key][1 if language == 'en' else 0].format(**values)


def error_text(error, language):
    if isinstance(error, UserError):
        return translate(error.key, language, **error.values)
    return str(error) if language == 'zh' else translate('technical', language, detail=str(error))


LOGS = {
    '等待相机完成上次服务连接退出，随后继续。': 'Waiting for the camera to finish leaving the previous service session before continuing.',
    '正在核对官方 2.01 固件包；此时尚未连接相机。': 'Verifying the official 2.01 package before connecting to the camera.',
    '正在离线提取两份中文 LTT 与共享图标 TTF，可能需要几分钟。': 'Extracting two Chinese LTT fonts and the shared icon TTF offline. This may take a few minutes.',
    '核对相机已有中文资源，已有且完全一致的文件会跳过。': 'Checking existing camera fonts. Exact matches will be skipped.',
    '正在解除所需属性的保护并设置语言。': 'Unlocking the required properties and setting languages.',
    '正在恢复原有语言保护。': 'Restoring original language protection.',
    '语言设置与保护已读回核对。': 'Language settings and protection passed read-back verification.',
    '两份中文 LTT 与图标 TTF 均已读回核对。': 'Both Chinese LTT fonts and the icon TTF passed read-back verification.',
    '本次读回通过。请断开 USB，关机再开机，检查语言菜单，再连接进行只读核对。': 'Read-back passed. Disconnect USB, restart, check the language menus, then reconnect for read-only verification.',
    '已确认 ILCE-7CM2，正在切换服务连接。': 'ILCE-7CM2 confirmed. Switching to the service connection.',
    '服务连接已就绪。': 'Service connection ready.',
}


def log_text(message, language):
    if language != 'en':
        return message
    if message in LOGS:
        return LOGS[message]
    for prefix, english in [('文件已匹配，跳过：', 'Exact match; skipped: '), ('正在补入：', 'Restoring: '),
                            ('本机记录：', 'Local record: '), ('检测记录：', 'Detection log: '), ('已停止：', 'Stopped (original details): ')]:
        if message.startswith(prefix):
            return english + message[len(prefix):]
    return message if message.isascii() else translate('technical', 'en', detail=message)
