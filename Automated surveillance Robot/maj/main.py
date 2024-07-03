import os
import re
import error_handler
import time
import ssl
import certifi
import webbrowser
from kivymd.toast import toast as toaster
from kivymd.app import MDApp
from kivy.lang.builder import Builder
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import Screen
from kivymd.uix.transition.transition import MDFadeSlideTransition
from kivy.core.window import EventLoop
from kivy.clock import Clock
from kivy.utils import platform
from threading import Thread
from kivymd.uix.swiper.swiper import MDSwiperItem
from kivymd.uix.taptargetview import MDTapTargetView
from kivymd.uix.dialog.dialog import MDDialog
from kivymd.uix.button.button import MDFlatButton
from kivy.properties import StringProperty
from client_handler import Client


# for security purpose
# DEFAULT@SECLEVEL=3 cipher suite string is used
# the set of cipher suites recommended by the current security standards and the highest level of security 'SECLEVEL=3'
context = ssl.SSLContext
context.set_ciphers(context(), "DEFAULT@SECLEVEL=3")
context.minimum_version = ssl.TLSVersion.TLSv1_3
context.check_hostname = True

# Load the server's certificate and set up verification options
context.load_verify_locations(context(), certifi.where())
context.verify_mode = ssl.CERT_REQUIRED

# this creates a default ssl context with the highest level of security
ssl._create_default_https_context = context

if platform == 'android':
    import AndroidNotificationManager
    from jnius import autoclass

    PythonActivity = autoclass("org.kivy.android.PythonActivity")
    mActivity = PythonActivity.mActivity

    AndroidNotificationManager.create_channels()

# connection_time_out = 10  # 30s



def regex_match_ip(ip: str) -> bool:
    """
    validates ip address regex'
    :param ip: IP address
    :return: boolean value if it is a valid ip or not
    """
    if re.search(r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', ip):
        return True
    return False
    # Both are copied from bing
    # if re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', ip):
    #     return True
    # return False


dialog1_message = ''
dialog1_text = 'Close'
dialog1_title = 'Error'


def dialog_type1(message='No internet connection!!!', button_text='close', title='Error'):
    global dialog1_message, dialog1_text, dialog1_title
    dialog1_message = message
    dialog1_text = button_text
    dialog1_title = title
    Clock.schedule_once(_dialog_type1, 0.2)


def _dialog_type1(_=None):
    button = MDFlatButton(text=dialog1_text,
                          theme_text_color="Custom",
                          text_color=app.theme_cls.primary_color)
    dialog = MDDialog(text=dialog1_message,
                      title=dialog1_title,
                      buttons=[button])
    if app.is_board_crash and dialog1_message.startswith('Board crashed'):
        button.bind(on_release=stop_app)
    button.bind(on_release=dialog.dismiss)
    dialog.open()


dialog2_message = ''
dialog2_title = ''
dialog2_button1 = 'Close'
dialog2_button = []


def dialog_type2(message, title='Error detected', button1='Close', button2='Send', on_press_button2=lambda x=None: x):
    global dialog2_title, dialog2_message, dialog2_button, dialog2_button1
    dialog2_title = title
    dialog2_message = message
    dialog2_button = [button2, on_press_button2]
    dialog2_button1 = button1
    Clock.schedule_once(_dialog_type2, 0.1)


def _dialog_type2(_=None):
    button1 = MDFlatButton(text=dialog2_button1,
                           theme_text_color="Custom",
                           text_color=app.theme_cls.primary_color)
    button2 = MDFlatButton(text=dialog2_button[0],
                           theme_text_color="Custom",
                           text_color=app.theme_cls.primary_color,
                           on_release=dialog2_button[1])
    dialog = MDDialog(text=dialog2_message,
                      title=dialog2_title,
                      buttons=[button1, button2])
    button1.bind(on_release=dialog.dismiss)

    dialog.open()


def minimize_app():
    activity = autoclass('org.kivy.android.PythonActivity').mActivity
    activity.moveTaskToBack(True)


last_toast_message = ""
last_toast_time = 0
toast_message = ""


def toast(message="Hello"):
    global last_toast_message, last_toast_time, toast_message
    if last_toast_message == message and time.time() - last_toast_time < 2.5:
        return
    else:
        toast_message = message
        Clock.schedule_once(_toast, 0.1)
        last_toast_message = message
        last_toast_time = time.time()


def _toast(_=None):
    toaster(toast_message)


def stop_app():
    app.on_stop()
    app.stop()


last_esc_down = 0


def hook_keyboard(_, key, *__):
    global last_esc_down
    if key == 27:  # escape button in windows and back button on android
        if sm.current in ('auto', 'manual'):
            change_screen('home')
            return True
        elif sm.current == 'help':
            change_screen('connect')
            return True
        elif sm.current == 'loading':
            change_screen(previous_screen)
            return True
        else:
            if time.time() - last_esc_down < 2:
                stop_app()
            toast("Press again to exit")
            last_esc_down = time.time()
            return True

    elif key == 13:  # enter key
        if sm.current == 'connect':
            connect.connect()


current_screen = previous_screen = 'connect'


def change_screen(screen):
    global current_screen
    current_screen = screen
    Clock.schedule_once(_set_screen, 0.1)


def _set_screen(_):
    global previous_screen
    print(current_screen)
    if previous_screen != current_screen and sm.current != 'loading':
        previous_screen = sm.current
    try:
        sm.current = current_screen
    except ValueError:
        pass


def notify_user(alert: str):
    # TODO: notification id
    if alert.startswith('FIRE:'):
        title = 'Fire alert'
        text = alert[5:]
        AndroidNotificationManager.show_notification(title, text, AndroidNotificationManager.FIRE_CHANNEL_ID, 1)
    elif alert.startswith('THEFT:'):
        title = 'Motion detected'
        text = alert[6:]
        AndroidNotificationManager.show_notification(title, text, AndroidNotificationManager.THEFT_CHANNEL_ID, 2)
    elif alert.startswith('LPG:'):
        title = 'LPG gas detected'
        text = alert[4:]
        AndroidNotificationManager.show_notification(title, text, AndroidNotificationManager.LPG_ALERT_CHANNEL_ID, 3)
    else:
        alert_ = alert.split(':')
        title = alert_[0].capitalize()
        text = ':'.join(alert_[1:])
        AndroidNotificationManager.show_notification(title, text, AndroidNotificationManager.RUNNING_SERVICES_CHANNEL_ID, 0)


def permission_callback(*args):
    pass


def get_permissions(*_):
    from android.permissions import request_permissions, Permission
    request_permissions([Permission.READ_EXTERNAL_STORAGE,
                         Permission.WRITE_EXTERNAL_STORAGE,
                         Permission.INTERNET,
                         Permission.ACCESS_NETWORK_STATE,
                         Permission.MANAGE_EXTERNAL_STORAGE,
                         Permission.ACCESS_WIFI_STATE],
                        callback=permission_callback)


def check_file_permission():
    if platform == 'android':
        try:
            os.listdir('/storage/emulated/0/')
            return True
        except PermissionError:
            return False
    else:
        return True


class BackgroundFlowController:
    @property
    def run(self):
        return bg_flow_control_h.run

    @run.setter
    def run(self, val):
        bg_flow_control_h.run = val

    @property
    def kw_args(self):
        return bg_flow_control_h.kw_args

    @property
    def get_function(self):
        return bg_flow_control_h.get_func

    @property
    def toast(self):
        return bg_flow_control_h.kw_args

    @toast.setter
    def toast(self, val):
        toast(val)


class BackgroundFlowControlHandler:
    _run = True
    _kw_args = {}

    def __init__(self, func):
        self._func = func

    @property
    def run(self):
        return self._run

    @run.setter
    def run(self, value: bool):
        self._run = bool(value)

    @property
    def kw_args(self):
        return self._kw_args

    @kw_args.setter
    def kw_args(self, val: dict):
        self._kw_args = val

    @property
    def get_func(self):
        return self._func

    @get_func.setter
    def get_func(self, val):
        self._func = val


class MySwiper(MDSwiperItem):
    image = StringProperty()
    text = StringProperty()

    def __init__(self, text="Hello world", image_path="foo.jpg", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image = image_path
        self.text = text


class HomeScreen(Screen):
    def change_mode(self, mode):
        if client.is_connected and client.IP is not None:
            change_screen(mode)


class AutomaticScreen(Screen):
    def on_enter(self):
        app.start_background_service()


class ManualScreen(Screen):
    pass


class ConnectScreen(Screen):
    ip = None
    tap_target = None
    is_tap_target_shown = False
    entry_time = time.time()

    def on_enter(self):
        Thread(target=self.wait_for_tap_target, daemon=True).start()
        # self.show_tap_target()

    def wait_for_tap_target(self):
        while time.time() - self.entry_time <= 30 and app.have_ip:  # this makes tap-target to open at beginning
            time.sleep(10)
        if sm.current == 'connect' and self.is_tap_target_shown is False:
            Clock.schedule_once(self.show_tap_target, 0.1)
            self.is_tap_target_shown = True

    def show_tap_target(self, _=None):
        tap_target = MDTapTargetView(
            widget=self.ids['help_button'],
            title_text='Help button',
            description_text='This is help button,\nin case if don\'t know IP address,\n'
                             'Or don\'t know how to get IP address\npress this button',
            widget_position='right_top',
            cancelable=True,
        )
        tap_target.start()

    def text_focus(self, instance):
        instance.isFocus = not instance.isFocus
        self.entry_time = time.time()
        if not instance.isFocus:
            if not instance.text:
                instance.helper_text = 'This field is required'
                instance.error = True
            elif not regex_match_ip(self.ids['ip'].text):
                instance.helper_text = 'Invalid IP address'
                instance.error = True
            else:
                instance.error = False

    def text_input(self):
        ip = self.ids['ip'].text
        self.entry_time = time.time()
        if regex_match_ip(ip):
            self.ids['connect'].disabled = False
        else:
            self.ids['connect'].disabled = True

    def connect(self, ip: str = None):
        if self.ids['connect'].disabled and ip is None:  # this function can also be called by pressing enter
            return
        if ip is None:
            ip_address = self.ids['ip'].text
        else:
            if not regex_match_ip(ip):
                toast('Invalid  IP address')
                return False
            self.ids['ip'].text = ip_address = ip
        change_screen('loading')
        process = Thread(target=client.connect, args=[ip_address, self.interrupt_handler], daemon=True)
        # socket.setdefaulttimeout(connection_time_out)
        process.start()

    def interrupt_handler(self, ip: str = None):
        if client.is_connection_failed:
            change_screen('connect')
        elif not client.test_server():
            change_screen('connect')
        elif client.is_connected and client.is_server_tested:
            change_screen('home')
            toast('Connection successful')
            self.ip = ip

    def helper(self):
        change_screen('help')


class HelpScreen(Screen):
    def on_enter(self):
        self.ids['swiper'].set_current(0)


class LoadingScreen(Screen):
    pass


class MainApp(MDApp):
    old_ip = None
    have_ip = False
    is_connected = False
    is_board_crash = False
    board_crash_info = ''

    def start_background_service(self):
        client.send('MODE:AUTO')
        Thread(target=client.receive_thread, daemon=True).start()

        # cls_name = 'BackgroundFlowController'
        #
        # Intent = autoclass('android.content.Intent')
        # try:
        #     background_service = autoclass('ranji.minipro.robot.ServiceBackgroundService')
        # except:
        #     import os
        #     import traceback
        #     from kvdroid.tools import share_file
        #     p = os.getcwd() + '/log/error.txt'
        #     with open(p, 'w+') as file:
        #         file.write(traceback.format_exc())
        #
        #     time.sleep(1)
        #     share_file(p)
        # intent = Intent(mActivity, background_service)
        #
        # intent.putExtra('class_name', cls_name)
        #
        # bg_flow_control_h.run = True
        # notify_user('Running service:Background service is running')
        #
        # mActivity.startService(intent)

    def minimize_app(self):
        if platform != 'android':
            client.send('Hello world')
        else:
            minimize_app()

    def launch_website(self):
        client.run = False
        client.send('LAUNCH_WEB')
        time.sleep(1)
        change_screen('connect')
        webbrowser.open(f'http://{client.IP}')
        self.disconnect_server()

    def error(self, msg):
        # print(msg)
        if msg == 'ConnectionFailed':
            dialog_type1('Connection failed, check IP address', 'Close')
            # client.disconnect()
            change_screen('connect')
        elif msg == 'TimeOutError':
            dialog_type1('Connection time out', 'Close')
            change_screen('connect')
            # client.disconnect()
        elif msg == 'Unicode error':
            toast('Unicode error trying again')
        else:
            dialog_type1(msg)

    def disconnect_server(self):
        bg_flow_control_h.run = False
        client.disconnect()

    def new_data_manager(self, data: str):
        if data.startswith('ERROR'):
            self.is_board_crash = True
            self.board_crash_info += data[5:]
        elif data == 'EndError' and self.is_board_crash:
            error_handler.write_log(self.board_crash_info, 'Robot')
            dialog_type2('Board crashed please check robot, for safety this app will close itself',
                         button2='Okay',
                         on_press_button2=self.stop)
        elif data.startswith('ALERT:'):
            alert_message = data[6:]
            notify_user(alert_message)

    def on_start(self):
        EventLoop.window.bind(on_keyboard=hook_keyboard)
        # Window.softinput_mode = "resize"
        # p = Thread(target=self.try_last_ip, daemon=True)
        # # change_screen('connect')
        # p.start()
        self.fps_monitor_start()
        Clock.schedule_once(self.try_last_ip)
        if not check_file_permission():
            dialog_type2('This app is still in development it may crash, '
                         'Inorder to improve the app performance and fix bugs please provide file permission',
                         button2="I'll do",
                         button1='No thanks',
                         on_press_button2=get_permissions)

    def try_last_ip(self, _=None):
        try:
            with open('last_ip.txt', 'r') as file:
                ip = file.read()
                self.old_ip = ip
                self.have_ip = True
        except FileNotFoundError:
            self.have_ip = False

        if self.have_ip and regex_match_ip(self.old_ip):
            connect.connect(self.old_ip)
        else:
            change_screen('connect')

    def on_stop(self):
        if not client.is_connection_failed and client.is_server_tested:
            with open('last_ip.txt', 'w+') as file:
                file.write(str(client.IP))

    def build(self):
        return sm


if __name__ == "__main__":
    app = MainApp()

    sm = MDScreenManager(transition=MDFadeSlideTransition())

    home = HomeScreen(name='home')
    auto = AutomaticScreen(name='auto')
    manual = ManualScreen(name='manual')
    connect = ConnectScreen(name='connect')
    help_screen = HelpScreen(name='help')
    loading = LoadingScreen(name='loading')

    sm.add_widget(loading)  # adding loading 1st prevents HomeScreen button being accessed before connection
    sm.add_widget(home)
    sm.add_widget(auto)
    sm.add_widget(manual)
    sm.add_widget(connect)
    sm.add_widget(help_screen)

    # sm.current = 'help'

    client = Client(app.error, new_message_interrupt=app.new_data_manager, port=1024)

    bg_flow_control_h = BackgroundFlowControlHandler(client.receive)
    bg_flow_control_h.kw_args = {'call_error': False}
    bg_flow_control_h.run = False

    try:
        app.run()
    except SystemExit:
        pass
    except:
        import traceback

        err = traceback.format_exc()
        toast(err)
        err += '________________________________________ENDS________________________________________\n\n'
        try:
            error_handler.write_log(err)
        except PermissionError:
            pass
