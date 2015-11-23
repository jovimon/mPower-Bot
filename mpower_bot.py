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
__version__ = 0.2

import requests
import telegram
import ConfigParser
import sys
import time
import logging

def mpower_login(mpower_ip, mpower_user, mpower_pass, mpower_cookie):
  s = requests.Session()
  cookies = { 'AIROS_SESSIONID': mpower_cookie }
  s.cookies.update(cookies)
  data = { 'username': mpower_user, 'password': mpower_pass }
  r = s.post('http://' + mpower_ip + '/login.cgi', data = data, cookies = cookies, allow_redirects=False)
  return s

def mpower_logout(mpower_session, mpower_ip):
  mpower_session.get('http://' + mpower_ip + '/logout.cgi', allow_redirects=False)
  
def mpower_get_status(config):

  mpower_ip = config.get('mPower','ip_address')
  mpower_cookie = config.get('mPower','cookie')
  mpower_user = config.get('mPower','user')
  mpower_pass = config.get('mPower','pass')

  mpower_session = mpower_login(mpower_ip, mpower_user, mpower_pass, mpower_cookie)

  r = mpower_session.get('http://' + mpower_ip + '/sensors')
  output = r.json()
  logging.debug("Status check result: " + r.text)
  # Output example:
  #{u'status': u'success', u'sensors': [
  #    {u'relay': 1, u'power': 0.0, u'thismonth': 0, u'lock': 0, u'prevmonth': 0, u'enabled': 0, 
  #      u'powerfactor': 0.0, u'current': 0.0, u'voltage': 235.893003463, u'output': 1, u'port': 1}
  #  ]}  
  sensor_num = len(output['sensors'])
  sensor = output['sensors'][0]
  sensor_id = sensor.get('port')
  status = "ON" if sensor.get('output') else "OFF"
  power = sensor.get('power')
  voltage = sensor.get('voltage')
  current = sensor.get('current')

  mpower_logout(mpower_session, mpower_ip)

  result = "This mPower has *%d* ports. Port *%d* is *%s*.\nImmediate consumption:\nPower: %.4fW\nCurrent: %.4fA\nVoltage: %.4fV" % (sensor_num, sensor_id, status, power, current, voltage)
  logging.info(result.replace('\n',' '))
  return result

def mpower_set_status(config, sensor_id, status):

  mpower_ip = config.get('mPower','ip_address')
  mpower_cookie = config.get('mPower','cookie')
  mpower_user = config.get('mPower','user')
  mpower_pass = config.get('mPower','pass')

  mpower_session = mpower_login(mpower_ip, mpower_user, mpower_pass, mpower_cookie)
  
  r = mpower_session.post('http://' + mpower_ip + '/sensors/' + sensor_id, data = {"output": status})
  logging.debug("Status update result: " + r.text)
  time.sleep(1)
  r = mpower_session.get('http://' + mpower_ip + '/sensors/' + sensor_id)
  output = r.json()
  logging.debug("Status check result: " + r.text)
  sensor_num = len(output['sensors'])
  sensor = output['sensors'][0]
  sensor_id = sensor.get('port')
  status = "Plugged ON" if sensor.get('output') else "Plugged OFF"
  power = sensor.get('power')
  voltage = sensor.get('voltage')
  current = sensor.get('current')

  mpower_logout(mpower_session, mpower_ip)

  result = "mPower port *%d* has been *%s* successfully.\nImmediate consumption:\nPower: %.4fW\nCurrent: %.4fA\nVoltage: %.4fV" % (sensor_id, status, power, current, voltage)

  logging.info(result.replace('\n',''))

  return result

def log_update(update):
  message = update.message.text.encode('utf-8')
  bot_chat_id = update.message.chat.id
  update_id = update.update_id
  first_name = update.message.from_user.first_name
  last_name = update.message.from_user.last_name
  from_id = update.message.from_user.id

  if logging.getLogger().getEffectiveLevel() == logging.DEBUG:
    logging.debug('Update %d from %s %s (%d) in chat %d received:', update_id,first_name, last_name, from_id, bot_chat_id)
    logging.debug(update)
  else:
    logging.info('Update %d from %s %s (%d) in chat %d: Received "%s"', update_id,first_name, last_name, from_id, bot_chat_id, message)

def main(argv):
  
  # Strip the script name
  my_name = argv[0].split('.')[0]
  # Default config file to be used
  cfg_file = my_name + '.cfg'

  # Read config file
  config = ConfigParser.ConfigParser()
  config.read(cfg_file)

  # Load config options
  logfile = config.get('Log','logfile')
  loglevel = config.getint('Log','loglevel')

  # Create file logger
  logging.basicConfig(filename=logfile, format='%(asctime)s | %(levelname)s | %(module)s | %(message)s', level=loglevel,  datefmt='%Y%m%d %H:%M:%S')

  logging.info("Starting %s Telegram Bot", my_name)

  # Create bot
  bot_token = config.get('Bot','token')
  bot = telegram.Bot(bot_token)

  # Warn if no chat_id configured
  if config.has_option('Bot','chat_id'):
    chat_id = config.getint('Bot','chat_id')
    logging.info('chat_id found. Only updates from your chat_id will be taken care of.')
  else:
    chat_id = -1
    logging.info('chat_id not found. Anyone can interact with your chat. Proceed with caution.')

  # Variable to keep the latest update_id when requesting for updates. 
  # It starts with the latest update_id if available.
  try:
    LAST_UPDATE_ID = bot.getUpdates()[-1].update_id
  except IndexError:
    LAST_UPDATE_ID = None

  while(True):

# {
# 	'message': {
# 		'from': {'first_name': u'Some', 'last_name': u'one', 'id': XXXXXXXXX}, 
# 		'contact': {'phone_number': '919932495762', 'first_name': u'Some', 'last_name': u'one', 'user_id': XXXXXXXXX}, 
# 		'chat': {'first_name': u'Some', 'last_name': u'one', 'type': u'private', 'id': XXXXXXXXX}, 
# 		'date': 1448276765, 
# 		'message_id': 102
# 	}, 
# 	'update_id': 751954550
# }
# {
#   'message': {
#     'from': {'first_name': u'Some', 'last_name': u'one', 'id': XXXXXXXXX}, 
#     'text': u'Cb', 
#     'chat': {'first_name': u'Some', 'last_name': u'one', 'type': u'private', 'id': XXXXXXXXX}, 
#     'date': 1448276772, 
#     'message_id': 103
#   }, 
#   'update_id': 751954551
# }
# {
#   'message': {
#     'from': {'username': u'Some_other', 'first_name': u'Some', 'last_name': u'other', 'id': XXXXXXXXX}, 
#     'text': u'/start', 
#     'chat': {'username': u'Some_other', 'first_name': u'Some', 'last_name': u'other', 'type': u'private', 'id': XXXXXXXXX}, 
#     'date': 1448276784, 
#     'message_id': 104
#   }, 
#   'update_id': 751954552
# }

    for update in bot.getUpdates(offset=LAST_UPDATE_ID, timeout=30):
      message = update.message.text.encode('utf-8')
      bot_chat_id = update.message.chat.id
      update_id = update.update_id

      log_update(update)
      if chat_id >= 0 and chat_id != bot_chat_id:
        logging.warning('Unauthorized chat_id %d found. Update ignored.', bot_chat_id)
        continue
      
      if '/check' == message:
        status = mpower_get_status(config)
        bot.sendMessage(chat_id = bot_chat_id, text=status, parse_mode=telegram.ParseMode.MARKDOWN)
 
      elif '/switch' == message:
        custom_keyboard = [["Turn on " + telegram.emoji.Emoji.FULL_MOON_WITH_FACE, "Turn off " + telegram.emoji.Emoji.NEW_MOON_WITH_FACE]] 
        reply_markup = telegram.ReplyKeyboardMarkup(keyboard=custom_keyboard, one_time_keyboard=True, resize_keyboard=True)
        bot.sendMessage(chat_id = bot_chat_id, text="What should I do?", reply_markup=reply_markup)

      elif 'Turn on ' + telegram.emoji.Emoji.FULL_MOON_WITH_FACE == message:
        status = mpower_set_status(config, sensor_id = "1", status = 1)
        reply_markup = telegram.ReplyKeyboardHide(hide_keyboard = True)
        bot.sendMessage(chat_id = bot_chat_id, text=status, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)

      elif 'Turn off ' + telegram.emoji.Emoji.NEW_MOON_WITH_FACE == message:
        status = mpower_set_status(config, sensor_id = "1", status = 0)
        reply_markup = telegram.ReplyKeyboardHide(hide_keyboard = True)
        bot.sendMessage(chat_id = bot_chat_id, text=status, parse_mode=telegram.ParseMode.MARKDOWN, reply_markup=reply_markup)

      else:
        bot.sendMessage(chat_id=bot_chat_id,
                        text='Welcome to mPower bot. Accepted commands:\n\n/check - Check mPower Status.\n/switch - Change mPower Status')

      LAST_UPDATE_ID = update_id + 1


if __name__ == '__main__':
  main(sys.argv)
