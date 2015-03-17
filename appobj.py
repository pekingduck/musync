from PyQt5 import QtCore #, QtGui, QtWidgets
import os, sys
import configparser
import music.device
import music.flac
import music.itunes
import widgets.foldermodel
import subprocess
import time
import re
import pprint

expusr = os.path.expanduser

class MusyncController(QtCore.QObject):
  class_map = { "iTunes" : music.itunes.Library, "FLAC" : music.flac.Library }
  
  def __init__(self, bundle_dir):
    super(MusyncController, self).__init__(None)
    self.init()
    self.bundle_dir = bundle_dir
    
  def init(self):
    self.config = configparser.ConfigParser()
    self.config.read(expusr("~/.music.cfg"))

  def init_db(self, lib_name):
    if lib_name in self.config:
      music.itunes.Library.genesis(lib_name, self.config)

  # get library and device data
  def metadata(self):
    data = {}
    lib_str = self.config["MAIN"]["LIBRARIES"].strip()
    libs = lib_str.split(",") if lib_str != '' else []
    for lib in libs:
      db = music.device.DB(self.select_db_file(lib))
      data[lib] = {}
      for dev in map(lambda n: db.get_device(n), db.devices()):
        data[lib][dev.name] = { 'loc' : dev.location,
                                'type' : dev.pl_type }
    return data
  
  def select(self, lib_name, device_name, dest, pl_type, event_cb, diag):
    db_file = self.db_file(lib_name)
    lib = self.class_map[self.config[lib_name]["TYPE"]](db_file)
    #selector = TreeSelector(lib_name)
    select_db = music.device.DB(self.select_db_file(lib_name))
    self.device = select_db.add_device(device_name, dest, pl_type)
    self.handler = event_cb

    model = widgets.foldermodel.FolderModel()

    # First lib
    for pl in lib.playlists():
      #selector.add_leaf(pl.path, self.device.get(pl.path), pl.size)
      model.mkdirp(pl.path_list, int(self.device.get(pl.path)), pl.size)
      self.handler()
      
    # Second Lib
    if 'SecondLib' in self.config[lib_name] and 'SecondLibPlaylistRegex' in self.config[lib_name]:
      lib_name2 = expusr(self.config[lib_name]["SecondLib"])
      lib2_regex = self.config[lib_name]["SecondLibPlaylistRegex"]
      db_file2 = self.db_file(lib_name2)
      lib2 = self.class_map[self.config[lib_name2]["TYPE"]](db_file2)
      rx = re.compile(lib2_regex)
      
      for pl in lib2.playlists():
        if re.search(rx, pl.path):
          model.mkdirp(pl.path_list, int(self.device.get(pl.path)), pl.size)
          #selector.add_leaf(pl.path, self.device.get(pl.path), pl.size)
        self.handler()
        
    diag.setModel(model)
    model.preprocess()
    if not diag.exec(): # "cancel" pressed
      return (0, 0)
    
    # Mark "D" for playlists not present in the selection
    to_be_deleted = {path:s for path,s in self.device.playlists()}
    for path_list, status, _, _ in model.checked():
      path = os.sep.join(path_list)
      self.device.set(path, status)
      if path in to_be_deleted:
        del to_be_deleted[path]
    for path in to_be_deleted:
      self.device.set(path, "D")

    num_deleted = self.device.delete_playlists(dest, pl_type)
    select_db.save_device(self.device)
    select_db.save()

    num_files = self.device.pre_sync(pl_type,
                                     self.staging_dir(lib_name),
                                     dest,
                                     self.handler)
    #print("delete {}, new {}".format(num_deleted, num_files))
    return (num_deleted, num_files)

  def sync(self):
    for progress, file_name in self.device.sync():
      yield (progress, file_name)
    
  def staging_dir(self, lib_name):
    return expusr(self.config[lib_name]["StagingDir"])

  def db_file(self, lib_name):
    return expusr(self.config[lib_name]["DBFile"])

  def select_db_file(self, lib_name):
    return expusr(self.config[lib_name]["SelectDBFile"])

  def delete_device(self, lib_name, device_name):
    db = music.device.DB(self.select_db_file(lib_name))
    if db.has_device(device_name):
      db.del_device(device_name)
      db.save()
