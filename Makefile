.PHONY:build
build: melpa
	cd melpa && git pull
	POOL_SIZE=30 python main.py

.PHONY: sample
sample: melpa
	MAX_PACKAGES=10 python main.py

melpa:
	git clone https://github.com/melpa/melpa.git

.PHONY: clean
clean:
	rm -f save.p
	rm -rf melpa

.PHONY: all
all: clean build
