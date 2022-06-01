ifeq ($(PREFIX),)
    PREFIX := /usr/local
endif

SCRIPT_NAME := noipv6-duc_1_0.py
SERVICE_NAME := noipv6-duc
CONFIG_DIR := $(PREFIX)/etc/noipv6-duc
CONFIG_PATH := $(CONFIG_DIR)/config.ini
SERVICE_PATH := /etc/systemd/system
SERVICE_USER := noipv6-duc

.all:
	echo "Please select target, e.g. install"

.PHONY: install
install:
	install -m 755 $(SCRIPT_NAME) $(PREFIX)/bin/
	[ -f $(CONFIG_PATH) ] && echo "Config $(CONFIG_PATH) already exists, dont overwrite" || install -D -m 644 config.ini $(CONFIG_PATH)
	useradd --no-create-home $(SERVICE_USER) || echo "cant create user $(SERVICE_USER), might already exist"
	install -m 644 $(SERVICE_NAME).service $(SERVICE_PATH)
	systemctl daemon-reload
	systemctl start $(SERVICE_NAME) || echo "Failed to start the service"
	echo "Install successful!"

.PHONY: uninstall
uninstall:
	systemctl stop $(SERVICE_NAME)
	rm $(SERVICE_PATH)/$(SERVICE_NAME).service
	systemctl daemon-reload
	userdel $(SERVICE_USER)
	rm "$(PREFIX)/bin/$(SCRIPT_NAME)"
	rm "$(CONFIG_PATH)" || echo "Cant delete $(CONFIG_PATH), might been deleted by user"
	rmdir $(CONFIG_DIR) || echo "Cant delete $(CONFIG_DIR), there might be remaining files"
	echo "Uninstall successful!"
