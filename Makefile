# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# This is <Makefile>
# -----------------------------------------------------------------------------
#
# REVISION AND CHANGES
# 2017/11/26        V0.1    Daniel Armbruster
# =============================================================================
#
# PURPOSE:
# --------
# Install EIDA NG Mediator/Federator webservices.
#
# USAGE:
# ------
# Display a list of EIDA NG webservices available to be installed:
#
# 	$ make ls
#
# ----
# To install a specific EIDA NG webservice invoke:
#
# 	$ make install \
# 		SERVICES="whitespace separated list of EIDA NG services to install"
#
# To install all EIDA NG webservices available invoke:
# 	
# 	$ make install
#
# ----
# Invoke
#
# 	$ make test [SERVICES=list of services]
#
# to run unittest facilities.
#
# ----
# To create a sphinx documentation run
#
# 	$ pip install sphinx
# 	$ make doc [SERVICES=list of services]
#
# NOTE:
# -----
# Since *virtualenv* is the preferred installation method, make sure the
# appropriate Python interpreter was activated before.
#
# =============================================================================

SERVICES_ALL=federator stationlite
# TODO(damb): Provide installation for all services
#SERVICES_ALL=federator mediator stationlite
SERVICES?=$(SERVICES_ALL)

PATH_EIDANGSERVICES=eidangservices
PATH_DOCS=docs

MANIFEST_IN=MANIFEST.in
MANIFEST_ALL=MANIFEST.in.all

BASENAME_DOC=docs
SPHINX_BUILDER=html
SPHINX_CHECK:=$(strip \
	$(shell python setup.py --help-commands | grep build_sphinx))
SPHINX_PKGS=$(sort $(dir $(wildcard $(PATH_EIDANGSERVICES)/*/)))
SPHINX_EXCLUDE=$(addsuffix /,$(addprefix $(PATH_EIDANGSERVICES)/,\
							 __pycache__ tests))

# -----------------------------------------------------------------------------
#
CHECKVAR=$(if $(filter $(1),$(SERVICES_ALL)),, \
	$(error ERROR: Invalid SERVICES parameter value: $(1)))
CHECKVARS=$(foreach var,$(1),$(call CHECKVAR,$(var)))

$(call CHECKVARS, $(SERVICES))

# -----------------------------------------------------------------------------
install: $(patsubst %,%.install,$(SERVICES))
sdist: $(patsubst %,%.sdist,$(SERVICES))
test: $(patsubst %,%.test,$(SERVICES))
doc: $(patsubst %,%.doc,$(SERVICES))

.PHONY: clean build-clean doc-clean
clean: build-clean doc-clean

build-clean:
	rm -rfv $(MANIFEST_IN)
	rm -rfv build
	rm -rfv *.egg-info

doc-clean:
	rm -rvf $(wildcard $(PATH_DOCS)/docs.*)

.PHONY: ls
ls:
	@echo "SERVICES available: \n$(SERVICES_ALL)"

# install services
%.install: $(PATH_EIDANGSERVICES)/%/$(MANIFEST_IN) $(MANIFEST_ALL)
	$(MAKE) build-clean
	cat $^ > $(MANIFEST_IN)
	python setup.py $(@:.install=) install
	
%.sdist: $(PATH_EIDANGSERVICES)/%/$(MANIFEST_IN) $(MANIFEST_ALL) 
	$(MAKE) build-clean
	cat $^ > $(MANIFEST_IN)
	python setup.py $(@:.sdist=) sdist

%.test: %.install
	python setup.py $(@:.test=) test

%.doc: $(PATH_DOCS)/sphinx.% %.make_docs_dest %.sphinx-apidoc
	python setup.py $(@:.doc=) build_sphinx \
	--build-dir $(PATH_DOCS)/$(BASENAME_DOC).$(@:.doc=)/ \
	-s $(word 1,$^)/source/ -b $(SPHINX_BUILDER)

# -----------------------------------------------------------------------------
# utility pattern rules

%.sphinx-apidoc: $(PATH_DOCS)/sphinx.%/source %.sphinx-service-exclude
	$(if $(SPHINX_CHECK),,$(error ERROR: sphinx not installed))
	sphinx-apidoc -M -o $< $(PATH_EIDANGSERVICES) \
		$(filter-out $(PATH_EIDANGSERVICES)/$(@:.sphinx-apidoc=)/, $(SPHINX_PKGS)) \
		$(SPHINX_EXCLUDE) $(SPHINX_SERVICE_EXCLUDE)

%.sphinx-service-exclude:
	$(eval SPHINX_SERVICE_EXCLUDE := $(addsuffix /tests/, \
		$(addprefix $(PATH_EIDANGSERVICES)/,$(@:.sphinx-service-exclude=))))

%.make_docs_dest:
	mkdir -pv $(PATH_DOCS)/$(BASENAME_DOC).$(@:.make_docs_dest=)

# ---- END OF <Makefile> ----
