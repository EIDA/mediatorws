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
# To install a specific EIDA NG webservice invoke:
#
# 	$ make install \
# 		SERVICES="whitespace separated list of EIDA NG services to install"
#
# Valid SERVICES parameter values are: 
# 	federator
# 
# To install EIDA NG webservices invoke:
# 	
# 	$ make install
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

# -----------------------------------------------------------------------------
#
CHECKVAR=$(if $(filter-out $(1),$(SERVICES_ALL)), \
	$(error ERROR: Invalid SERVICES parameter value: $(1)),)
CHECKVARS=$(foreach var,$(1),$(call CHECKVAR,$(var)))

$(call CHECKVARS, $(SERVICES))

# -----------------------------------------------------------------------------
install: $(patsubst %,%.install,$(SERVICES))
sdist: $(patsubst %,%.sdist,$(SERVICES))

# install services
%.install: $(PATH_EIDANGSERVICES)/%/MANIFEST.in
	cp $< .
	python setup.py $(@:.install=) install
	
%.sdist: $(PATH_EIDANGSERVICES)/%/MANIFEST.in
	cp $< .
	python setup.py $(@:.sdist=) sdist


# ---- END OF <Makefile> ----
