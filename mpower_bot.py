#!/usr/bin/env python
# encoding: utf-8
#
# Ubiquiti's mPower (www.ubnt.com/mfi/mpower/) Telegram Bot
# Copyright (C) 2015 @jovimon - @hflistener
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see [http://www.gnu.org/licenses/].

__author__ = '@jovimon - @hflistener'
__version__ = 0.1


import requests
import telegram
import ConfigParser
import sys
import time

def usage(myself):
  print "%s.py - Ubiquiti mPower Telegram Bot" % myself
  print "Authors: @jovimon - @hflistener"
  print ""
  print "Usage: python %s.py" % myself

def mpower_login(mpower_ip, mpower_user, mpower_pass, mpower_cookie):
  s = requests.Session()
  cookies = { 'AIROS_SESSIONID': mpower_cookie }
  s.cookies.update(cookies)
  data = { 'username': mpower_user, 'password': mpower_pass }
  r = s.post('http://' + mpower_ip + '/login.cgi', data = data, cookies = cookies)
  return s

def mpower_logout(mpower_session, mpower_ip):
  mpower_session.get('http://' + mpower_ip + '/logout.cgi', allow_redirects=False)
  
def mpower_get_status(mpower_session, mpower_ip):
  r = mpower_session.get('http://' + mpower_ip + '/sensors/1')
  output = r.json()
  # Output example:
  #{u'status': u'success', u'sensors': [{u'relay': 1, u'power': 0.0, u'thismonth': 0, u'lock': 0, u'prevmonth': 0, u'enabled': 0, u'powerfactor': 0.0, u'current': 0.0, u'voltage': 235.893003463, u'output': 1, u'port': 1}]}
  sensor_num = len(output['sensors'])
  sensor = output['sensors'][0]
  sensor_id = sensor.get('port')
  status = "ON" if sensor.get('output') else "OFF"
  power = sensor.get('power')
  voltage = sensor.get('voltage')
  current = sensor.get('current')
  result = "This mPower has *%d* ports. Port *%d* is *%s*.\nImmediate consumption:\nPower: %.4fW\nCurrent: %.4fA\nVoltage: %.4fV" % (sensor_num, sensor_id, status, power, current, voltage)
  return result

def mpower_set_status(mpower_session, mpower_ip, mpower_sensor_id, mpower_status):
  r = mpower_session.post('http://' + mpower_ip + '/sensors/' + mpower_sensor_id, data = {"output": mpower_status})
  time.sleep(3)
  r = mpower_session.get('http://' + mpower_ip + '/sensors/' + mpower_sensor_id)
  output = r.json()
  print output
  # Output example:
  #{u'status': u'success', u'sensors': [{u'relay': 1, u'power': 0.0, u'thismonth': 0, u'lock': 0, u'prevmonth': 0, u'enabled': 0, u'powerfactor': 0.0, u'current': 0.0, u'voltage': 235.893003463, u'output': 1, u'port': 1}]}
  sensor_num = len(output['sensors'])
  sensor = output['sensors'][0]
  sensor_id = sensor.get('port')
  status = "Plugged ON" if sensor.get('output') else "Plugged OFF"
  power = sensor.get('power')
  voltage = sensor.get('voltage')
  current = sensor.get('current')
  result = "mPower port *%d* has been *%s* successfully.\nImmediate consumption:\nPower: %.4fW\nCurrent: %.4fA\nVoltage: %.4fV" % (sensor_id, status, power, current, voltage)
  return result


def main(argv):
  
  # Strip the script name
  my_name = argv[0].split('.')[0]
  # Default config file to be used
  cfg_file = my_name + '.cfg'
  
  print "Starting %s Telegram Bot" % my_name

  # Read config file
  config = ConfigParser.ConfigParser()
  config.read(cfg_file)

  # Load config options
  bot_token = config.get('Bot','token')
  mpower_ip = config.get('mPower','ip_address')
  mpower_cookie = config.get('mPower','cookie')
  mpower_user = config.get('mPower','user')
  mpower_pass = config.get('mPower','pass')

  # Create bot
  bot = telegram.Bot(bot_token)

  # Variable to keep the latest update_id when requesting for updates. 
  # It starts with the latest update_id if available.
  try:
    LAST_UPDATE_ID = bot.getUpdates()[-1].update_id
  except IndexError:
    LAST_UPDATE_ID = None

  while(True):

    for update in bot.getUpdates(offset=LAST_UPDATE_ID, timeout=10):
      message = update.message.text.encode('utf-8')
      bot_chat_id = update.message.chat.id
      update_id = update.update_id

      print 'Update %d: Received "%s"' % (update_id, message)

      if '/check' == message:
        mpower_session = mpower_login(mpower_ip, mpower_user, mpower_pass, mpower_cookie)
        status = mpower_get_status(mpower_session, mpower_ip)
        bot.sendMessage(chat_id = bot_chat_id, text=status, parse_mode=telegram.ParseMode.MARKDOWN)
        mpower_logout(mpower_session, mpower_ip)
 
      elif '/switch' == message:
        custom_keyboard = [["Turn on " + telegram.emoji.Emoji.FULL_MOON_WITH_FACE, "Turn off " + telegram.emoji.Emoji.NEW_MOON_WITH_FACE]] 
        reply_markup = telegram.ReplyKeyboardMarkup(keyboard=custom_keyboard, one_time_keyboard=True, resize_keyboard=True)
        bot.sendMessage(chat_id = bot_chat_id, text="What should I do?", reply_markup=reply_markup)

      elif 'Turn on ' + telegram.emoji.Emoji.FULL_MOON_WITH_FACE == message:
        mpower_session = mpower_login(mpower_ip, mpower_user, mpower_pass, mpower_cookie)
        status = mpower_set_status(mpower_session, mpower_ip, "1", 1)
        reply_markup = telegram.ReplyKeyboardHide(hide_keyboard = True)
        bot.sendMessage(chat_id = bot_chat_id, text=status, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)
        mpower_logout(mpower_session, mpower_ip)

      elif 'Turn off ' + telegram.emoji.Emoji.NEW_MOON_WITH_FACE == message:
        mpower_session = mpower_login(mpower_ip, mpower_user, mpower_pass, mpower_cookie)
        status = mpower_set_status(mpower_session, mpower_ip, "1", 0)
        reply_markup = telegram.ReplyKeyboardHide(hide_keyboard = True)
        bot.sendMessage(chat_id = bot_chat_id, text=status, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)
        mpower_logout(mpower_session, mpower_ip)

      else:
        bot.sendMessage(chat_id=bot_chat_id,
                        text='Welcome to mPower bot. Accepted commands:\n\n/check - Check mPower Status.\n/switch - Change mPower Status')

      LAST_UPDATE_ID = update_id + 1


if __name__ == '__main__':
  main(sys.argv)
