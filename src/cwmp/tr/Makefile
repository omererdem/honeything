default: all

all: stamp.parsed

SCHEMA_IN = $(wildcard schema/tr-*.xml) $(wildcard schema/x-*.xml) $(wildcard ../platform/*/schema/x-*.xml)
stamp.parsed: parse-schema.py ${SCHEMA_IN}
	rm -f $@ $@.new tr???_*.py* ../platform/*/schema/x_*.py*
	rm -rf std
	./parse-schema.py ${SCHEMA_IN}
	touch $@
	
stamp.validated: stamp.parsed *.py
	rm -f $@ $@.new
	( \
		for d in $(patsubst %.py,%,$(wildcard tr???_*.py)); do \
			echo "import $$d"; \
		done; \
	) >$@.new
	python $@.new
	mv $@.new $@

test: all stamp.validated $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		echo; \
		echo "Testing $$d"; \
		python $$d; \
	done

clean:
	rm -f *~ .*~ *.pyc *.stamp tr???_*.py* x_*.py* stamp.*
	rm -rf std
