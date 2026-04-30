.PHONY: setup dev start stop status restart seed-user build test-e2e

setup:
	./start-dev.sh setup

dev start:
	./start-dev.sh start

stop:
	./start-dev.sh stop

status:
	./start-dev.sh status

restart:
	./start-dev.sh restart

seed-user:
	./start-dev.sh seed-user

build:
	./start-dev.sh build

test-e2e:
	cd web-dashboard && npm run test:e2e:circles
