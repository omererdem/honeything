default: all

all: test

test: all $(wildcard *_test.py)
	set -e; \
	for d in $(filter %_test.py,$^); do \
		echo; \
		echo "Testing $$d"; \
		python $$d; \
	done

clean:
	rm -f *~ .*~ *.pyc
