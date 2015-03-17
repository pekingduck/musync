APP = MuSync.app
widgets = framelessdialog.py progressdialog.py musyncwidget.py

all: clean $(widgets) app install

$(widgets): %.py: %.ui
	pyuic5 -o $@ $<

app:
	mkdir -p $(APP)/Contents/Resources/python
	mkdir -p $(APP)/Contents/MacOS

install:
	cp -p MuSync $(APP)/Contents/MacOS/
	cp -p *.py $(APP)/Contents/Resources/python
	cp -p Info.plist $(APP)/Contents
	cp -p MuSync.icns $(APP)/Contents/Resources

clean:
	rm $(widgets)
	rm -rf $(APP)
