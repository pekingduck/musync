APP = MuSync.app
widgets = framelessdialog.py progressdialog.py musyncwidget.py

all: $(widgets) app

$(widgets): %.py: %.ui
	pyuic5 -o $@ $<

app:
	mkdir -p $(APP)/Contents/Resources
	mkdir -p $(APP)/Contents/MacOS
	cp -p MuSync *.py $(APP)/Contents/MacOS/
	cp -p Info.plist $(APP)/Contents
	cp -p MuSync.icns $(APP)/Contents/Resources

clean:
	rm $(widgets)
	rm -rf $(APP)
