import kivy
kivy.require('1.11.1') # replace with your current kivy version !

from kivy.app import App
from kivy.lang import Builder
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.textinput import TextInput
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.config import Config
from kivy.properties import StringProperty
from kivy.uix.screenmanager import ScreenManager, Screen
Config.set('graphics','width',300)
Config.set('graphics','height',600)



class MainScreen(Screen):
    btc_balance=1234567
    usd_balance=100000000
    btc_balance_text = StringProperty(str(btc_balance) + " BTC")
    usd_balance_text = StringProperty("~100 billion USD")
    font_size = "20sp"
    
    def update_balance(self):
        self.btc_balance_text =  str(self.btc_balance*1.5) + " BTC"
        self.usd_balance_text = "~150 billion USD"
        
        
class SendScreen(Screen):
  
    def confirm_popup(self):
        self.show = ConfirmSendPopup()
        self.popupWindow = Popup(title="Confirm Transaction", content=self.show, size_hint=(None,None), size=(280,280), 
                            #auto_dismiss=False
                           )
        self.popupWindow.open()
        
    def cancel_tx(self):
        self.popupWindow.dismiss()
        
        
class ConfirmSendPopup(FloatLayout):
    def checkout(self,*args):
        if args[1]>28:
            print("CONFIRMED")
    pass
 

class WindowManager(ScreenManager):
    pass




kv = Builder.load_file("walletgui.kv")


class walletguiApp(App):
    title = "Wallet"
    def build(self):
        return kv


if __name__ == '__main__':
    walletguiApp().run()
    
    