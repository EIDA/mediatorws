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
# 	$ make tests [SERVICES=list of services]
#
# to run unittest facilities.
#
# NOTE:
# -----
# Since *virtualenv* is the preferred installation method, make sure the
# appropriate Python interpreter was activated before.
#
# =============================================================================

SERVICES_ALL=federator
# TODO(damb): Provide installation for all services
#SERVICES_ALL=federator mediator stationlite
SERVICES?=$(SERVICES_ALL)

PATH_EIDANGSERVICES=eidangservices
MANIFEST_IN=MANIFEST.in
MANIFEST_ALL=MANIFEST.in.all

# -----------------------------------------------------------------------------
#
CHECKVAR=$(if $(filter-out $(1),$(SERVICES_ALL)), \
	$(error ERROR: Invalid SERVICES parameter value: $(1)),)
CHECKVARS=$(foreach var,$(1),$(call CHECKVAR,$(var)))

$(call CHECKVARS, $(SERVICES))

# -----------------------------------------------------------------------------
install: $(patsubst %,%.install,$(SERVICES))
sdist: $(patsubst %,%.sdist,$(SERVICES))
test: $(patsubst %,%.test,$(SERVICES))


.PHONY: build-clean
build-clean:
	rm -rfv $(MANIFEST_IN)
	rm -rfv build
	rm -rfv *.egg-info

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

# ---- END OF <Makefile> ----
