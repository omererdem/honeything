default: all


GPYLINT=gpylint --disable=W0403,W0613 \
	  --init-hook='sys.path.append("."); import tr.fix_path'


all: tr/all

test: all tr/test dm/test platform/gfmedia/test *_test.py
	set -e; \
	for d in $(filter %_test.py,$^); do \
		echo; \
		echo "Testing $$d"; \
		python $$d; \
	done

clean: tr/clean
	rm -f *~ .*~ *.pyc
	find . -name '*.pyc' -o -name '*~' | xargs rm -f

lint: all
	set -e; \
	find -name '*.py' -size +1c | \
	grep -v '/vendor/' | \
	grep -v '/\.' | \
	grep -v 'tr/tr..._.*\.py' | \
	grep -v 'tr/x_.*\.py' | \
	xargs $(GPYLINT)

%.lint: all
	$(GPYLINT) $*


DSTDIR?=/tmp/catawampus/
INSTALL=install

install:
	$(INSTALL) -d $(DSTDIR) $(DSTDIR)/tr  $(DSTDIR)/tr/vendor \
		$(DSTDIR)/tr/vendor/bup/lib/bup $(DSTDIR)/tr/vendor/pynetlinux \
		$(DSTDIR)/tr/vendor/tornado $(DSTDIR)/tr/vendor/tornado/tornado \
		$(DSTDIR)/tr/vendor/tornado/tornado/platform \
		$(DSTDIR)/tr/vendor/pbkdf2 $(DSTDIR)/tr/vendor/curtain \
		$(DSTDIR)/platform $(DSTDIR)/platform/gfmedia \
		$(DSTDIR)/platform/fakecpe $(DSTDIR)/dm
	$(INSTALL) -D -m 0755 cwmp cwmpd $(DSTDIR)
	$(INSTALL) -D -m 0644 *.py $(DSTDIR)
	$(INSTALL) -D -m 0644 tr/*.py $(DSTDIR)/tr
	$(INSTALL) -D -m 0644 dm/*.py $(DSTDIR)/dm
	$(INSTALL) -D -m 0644 platform/*.py $(DSTDIR)/platform
	$(INSTALL) -D -m 0644 platform/gfmedia/*.py $(DSTDIR)/platform/gfmedia
	$(INSTALL) -D -m 0644 platform/fakecpe/*.py $(DSTDIR)/platform/fakecpe
	$(INSTALL) -D -m 0644 platform/fakecpe/version $(DSTDIR)/platform/fakecpe
	$(INSTALL) -D -m 0644 tr/vendor/README.third_party $(DSTDIR)/tr/vendor
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/__init__.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/options.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -m 0644 tr/vendor/bup/lib/bup/shquote.py $(DSTDIR)/tr/vendor/bup/lib/bup
	$(INSTALL) -D -m 0644 tr/vendor/curtain/* $(DSTDIR)/tr/vendor/curtain
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/*.py $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/LICENSE.txt $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/pynetlinux/README* $(DSTDIR)/tr/vendor/pynetlinux
	$(INSTALL) -D -m 0644 tr/vendor/tornado/README $(DSTDIR)/tr/vendor/tornado
	$(INSTALL) -D -m 0644 tr/vendor/tornado/tornado/*.py $(DSTDIR)/tr/vendor/tornado/tornado
	$(INSTALL) -D -m 0644 tr/vendor/tornado/tornado/*.crt $(DSTDIR)/tr/vendor/tornado/tornado
	$(INSTALL) -D -m 0644 tr/vendor/tornado/tornado/platform/*.py $(DSTDIR)/tr/vendor/tornado/tornado/platform
	$(INSTALL) -D -m 0644 tr/vendor/xmlwitch.py $(DSTDIR)/tr/vendor
	$(INSTALL) -D -m 0644 tr/vendor/pbkdf2/* $(DSTDIR)/tr/vendor/pbkdf2
	python -mcompileall $(DSTDIR)

# Subdir rules
%/all:; $(MAKE) -C $* all
%/test:; $(MAKE) -C $* test
%/clean:; $(MAKE) -C $* clean
