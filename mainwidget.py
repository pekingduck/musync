from PyQt5 import QtCore, QtGui, QtWidgets
import os, sys
import musyncwidget
import progressdialog
import framelessdialog
import widgets.treeselector
import time

class FramelessDialog(QtWidgets.QDialog):
  def __init__(self, parent, msg):
    super(FramelessDialog, self).__init__(parent,
                                          QtCore.Qt.FramelessWindowHint)
    self.ui = framelessdialog.Ui_framelessDialog()
    self.ui.setupUi(self)
    self.ui.label.setText(msg)
    
class ProgressDialog(QtWidgets.QDialog):
  def __init__(self, parent, num_files):
    super(ProgressDialog, self).__init__(parent,
                                         QtCore.Qt.FramelessWindowHint)
    self.num_files = num_files
    self.ui = progressdialog.Ui_progressDiag()
    self.ui.setupUi(self)
    self.ui.progressBar.setMinimum(0)
    self.ui.progressBar.setMaximum(100)
    self.ui.progressBar.setValue(0)
    self.ui.fileNumLab.setText("")
    self.ui.fileLab.setText("")
    self.ui.buttonBox.setHidden(True)
    
  def update_progress(self, percentage, file_name, file_num):
    self.ui.fileNumLab.setText("Copying {} of {}".format(file_num,
                                                         self.num_files))
    self.ui.progressBar.setValue(percentage)
    self.ui.fileLab.setText(file_name)

  def exec(self):
    self.ui.buttonBox.setHidden(False)
    self.ui.fileLab.setAlignment(QtCore.Qt.AlignHCenter)
    super().exec()
    
class MusyncGUI(QtWidgets.QWidget):
  next_step = QtCore.pyqtSignal(str, str, str)
  device_selected = QtCore.pyqtSignal(str)

  def __init__(self, app_obj):
    super(MusyncGUI, self).__init__(None)
    self.app = app_obj
    self.data = app_obj.metadata()
    
    self.ui = musyncwidget.Ui_MusyncWidget()
    self.ui.setupUi(self)

    self.ui_dep_map = {
      self.ui: 1 }
    self.ui.libraryCB.addItems(sorted(self.data.keys()))
    self.ui.libraryCB.setFocus(True)
    
    self.ui.libraryCB.activated[str].connect(self.library_selected)
    self.ui.deviceCB.activated[str].connect(self.device_selected)
    self.ui.locationEdit.textChanged.connect(self.location_edited)
    self.ui.chooseButton.clicked.connect(self.choose_clicked)
    self.ui.cancelButton.clicked.connect(self.close)
    self.ui.deleteButton.clicked.connect(self.delete_device)
    self.ui.nextButton.clicked.connect(self.select_and_sync)
    self.ui.initButton.clicked.connect(self.init_clicked)
    self.ui.deviceCB.currentTextChanged.connect(self.device_check)
    self.ui.playlistCB.addItem("dir")
    self.ui.playlistCB.addItem("m3u8")

    if self.ui.libraryCB.count() > 0:
      self.ui.libraryCB.setCurrentIndex(0)
      self.library_selected(self.ui.libraryCB.currentText())
      
  def device_check(self, text):
    status = False
    if text:
      status = True
    self.ui.deleteButton.setEnabled(status)

  def delete_device(self):
    dev_name = self.ui.deviceCB.currentText()
    dev_idx = self.ui.deviceCB.currentIndex()
    #if self.sdb.has_device(dev_name):
    #  self.sdb.del_device(dev_name)
    #  self.sdb.save()
    self.app.delete_device(self.ui.libraryCB.currentText(), dev_name)
    self.ui.deviceCB.removeItem(dev_idx)
    self.ui.locationEdit.setText("")
    self.device_selected(self.ui.deviceCB.currentText())
    
  def init_clicked(self):
    lib_name = self.ui.libraryCB.currentText()
    diag = FramelessDialog(self, "Initializing Library...")
    diag.show()
    self.app.init_db(lib_name)
    diag.done(0)

  def choose_clicked(self):
    loc = QtWidgets.QFileDialog.getExistingDirectory(self, 
                                                     "Open Device", "/Volumes")
    if loc:
      self.ui.locationEdit.setText(loc)
      self.validate_input()

  def location_edited(self):
    self.validate_input()

  def validate_input(self):
    #print("validate_input")
    is_valid = False
    loc = os.path.expanduser(self.ui.locationEdit.text())
    if (loc and 
        os.access(loc, os.W_OK) and 
        #self.ui.libraryCB.currentIndex() and 
        len(self.ui.deviceCB.currentText())):
      is_valid = True
    self.ui.nextButton.setEnabled(is_valid)

  def enable(self, enabled):
    for w in [ "nextButton", "cancelButton", "locationEdit", "libraryCB",
               "deviceCB", "chooseButton", "deleteButton" ]:
      self.ui.__dict__[w].setEnabled(enabled)

  def library_selected(self, lib):
    dev_list = sorted(self.data[lib].keys())
    self.ui.deviceCB.clear()
    self.ui.initButton.setEnabled(True)
    self.ui.initButton.setText("Import")
    if len(dev_list):
      self.ui.deviceCB.addItems(dev_list)
      self.device_selected(dev_list[0])
    else:
      self.ui.locationEdit.setText("")

  def device_selected(self, name):
    lib = self.ui.libraryCB.currentText()
    # need to check this because a user can create a new device name
    # which isn't yet in the database
    if name in self.data[lib]:
      self.ui.locationEdit.setText(self.data[lib][name]['loc'])
      self.ui.deleteButton.setEnabled(True)
      i = self.ui.playlistCB.findText(self.data[lib][name]['type'])
      self.ui.playlistCB.setCurrentIndex(i)
      self.ui.playlistCB.setEnabled(False)
    else:
      self.ui.locationEdit.setText("")
      self.ui.playlistCB.setEnabled(True)
    self.validate_input()
    
  # let QT redraw widgets and processes other things (except user inputs)
  # during extended operations (e.g. exec()ing an external process)
  def process_events(self):
    QtWidgets.QApplication.processEvents(
      QtCore.QEventLoop.ExcludeUserInputEvents) 

  def selector_format_func(self, total_str, count_str):
    total = int(total_str)
    count = int(count_str)
    return "{:.2f}G / {} playlist(s) selected".format(total / 1024 ** 3, count)
  
  def select_and_sync(self):
    self.enable(False)   # grey out some controls

    dest = os.path.expanduser(self.ui.locationEdit.text())
    device_name = self.ui.deviceCB.currentText()
    pl_type = self.ui.playlistCB.currentText()
    lib_name = self.ui.libraryCB.currentText()
    diag = widgets.treeselector.TreeSelectorDialog(parent = self,
                                                   format_function = self.selector_format_func)

    # launch playlist selector
    (num_deleted, num_files) = self.app.select(lib_name,
                                               device_name,
                                               dest,
                                               pl_type,
                                               self.process_events,
                                               diag)

    if num_deleted > 0:
      diag = FramelessDialog(self, "{} playlist(s) deleted".format(num_deleted))
      diag.show()
      time.sleep(1)
      diag.done(0)

    if num_files > 0:
      diag = ProgressDialog(self, num_files)
      diag.show() # display the progress ("OK" is hidden)

      file_num = 0
      for progress, file_name in self.app.sync():
        if file_name is not None:
          file_num += 1
        else:
          # the last update => no file being transferred and progress @ 100%
          file_name = "Finished!"
        diag.update_progress(progress, file_name, file_num)
      diag.exec() # "OK" unhidden here, wait for user to click
      
    self.close() # the last widget closes and the app quits here
