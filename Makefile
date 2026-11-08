## Directories for CI artifacts
ARTIFACTS_DIR := target/ci-artifacts
ART_UNIT_DIR := $(ARTIFACTS_DIR)/unit
ART_PERF_DIR := $(ARTIFACTS_DIR)/performance
ART_COV_DIR := $(ARTIFACTS_DIR)/coverage
ART_LOGS_DIR := $(ARTIFACTS_DIR)/logs
JACOCO_SITE := target/site/jacoco
.PHONY: help install test tests all-tests test-unit perf-runner perf perf-fast format clean build run coverage \
	ci-clean ci-build ci-test-unit ci-test-perf ci-test-perf-fast ci-coverage ci-artifacts ci-all ci-all-fast show-jmh-json show-jmh-report

# Colors
GREEN  := $(shell tput -Txterm setaf 2)
YELLOW := $(shell tput -Txterm setaf 3)
WHITE  := $(shell tput -Txterm setaf 7)
RESET  := $(shell tput -Txterm sgr0)

# Help documentation
TARGET_MAX_CHAR_NUM=20

## Show help
help:
	@echo ''
	@echo 'Usage:'
	@echo '  ${YELLOW}make${RESET} ${GREEN}<target>${RESET}'
	@echo ''
	@echo 'Targets:'
	@awk '/^[a-zA-Z\_-]+:.*?## .*$$/ { \
		helpMessage = match(lastLine, /^## (.*)/); \
		if (helpMessage) { \
			helpCommand = substr($$1, 0, index($$1, ":")-1); \
			helpMessage = substr(lastLine, RSTART + 3, RLENGTH); \
			printf "  ${YELLOW}%-$(TARGET_MAX_CHAR_NUM)s${GREEN}%s${RESET}\n", helpCommand, helpMessage; \
		} \
	} \
	{ lastLine = $$0 }' $(MAKEFILE_LIST) | sort -u

## Install project dependencies
install: ## Install project dependencies
	@echo "${GREEN}Installing dependencies...${RESET}"
	mvn -DskipTests install

## Run complete pipeline (build → tests → coverage → benchmark)
all: build tests coverage perf ## Run complete pipeline without duplicate test runs

## Run all tests (alias)
all-tests: tests ## Run all tests (unit only)

## Convenience alias to run all tests
test: tests ## Run all tests (unit only)

## Run all tests (unit) once
tests: ## Run all unit tests once
	@echo "${GREEN}Running all unit tests...${RESET}"
	mvn -q test

## Run unit tests
test-unit: ## Run unit tests
	@echo "${GREEN}Running unit tests...${RESET}"
	mvn -q test

## (Removed) Integration tests are no longer part of this pipeline

## Run a specific test class
test-class: ## Run a specific test class (e.g., make test-class TEST=com.example.TestClass)
	@if [ -z "$(TEST)" ]; then \
		echo "${YELLOW}Please specify a test class with TEST=ClassName${RESET}"; \
		exit 1; \
	fi
	mvn test -Dtest=$(TEST)

## Run performance benchmarks via JMH runner (exec:java)
perf-runner: ## Run JMH using JmhBenchmarkRunner (skip tests)
	@echo "${GREEN}Running performance benchmarks via runner...${RESET}"
	mvn -q -DskipTests test-compile exec:java -Dexec.mainClass="org.purplebean.kmip.benchmark.JmhBenchmarkRunner"

## Run performance benchmarks (perf profile)
perf: ## Run performance benchmarks (perf profile)
	@echo "${GREEN}Running performance benchmarks...${RESET}"
	mvn -q -DskipTests verify -P perf \
		-Dbench.threads=$$(nproc) \
		-Dbench.wi=3 \
		-Dbench.mi=5 \
		-Dbench.wt.ms=10 \
		-Dbench.mt.ms=2

## Run fast performance benchmarks (perf-fast profile)
perf-fast: ## Run fast performance benchmarks (perf-fast profile)
	@echo "${GREEN}Running fast performance benchmarks...${RESET}"
	mvn -q -DskipTests verify -P perf-fast \
		-Dbench.threads=$$(nproc) \
		-Dbench.wi=1 \
		-Dbench.mi=1 \
		-Dbench.wt.ms=50 \
		-Dbench.mt.ms=100

## Format code (uses Spotless if configured, else skips)
format: ## Format code (Spotless optional)
	@echo "${GREEN}Formatting code...${RESET}"
	@if grep -q "spotless-maven-plugin" pom.xml; then \
		echo "- Spotless detected. Running spotless:apply"; \
		mvn spotless:apply; \
	else \
		echo "- Spotless not configured in pom.xml. Skipping format."; \
	fi

## Clean build artifacts
clean: ## Clean build artifacts
	@echo "${GREEN}Cleaning...${RESET}"
	mvn clean

## Build the project (no implicit clean to avoid double-clean). Use `make clean` explicitly if needed.
build: install ## Build the project

## Run the application (optional; requires Spring Boot plugin)
run: ## Run the application (if spring-boot plugin is configured)
	@echo "${GREEN}Running application...${RESET}"
	@if grep -q "spring-boot-maven-plugin" pom.xml; then \
		mvn spring-boot:run; \
	else \
		echo "- Spring Boot plugin not configured in pom.xml. Nothing to run. Skipping."; \
	fi

## Generate code coverage report without rerunning tests
coverage: ## Generate code coverage report (reuses previous test run)
	@echo "${GREEN}Generating code coverage report from existing execution data...${RESET}"
	mvn -DskipTests jacoco:report
	@echo "${GREEN}Report generated at:${RESET} file://$(shell pwd)/target/site/jacoco/index.html"

## Show latest JMH JSON results (if present)
show-jmh-json: ## Show path to JMH JSON results
	@if [ -f target/jmh-results.json ]; then \
		echo "${GREEN}JMH JSON:${RESET} file://$(shell pwd)/target/jmh-results.json"; \
	else \
		echo "${YELLOW}No JMH JSON found at target/jmh-results.json${RESET}"; \
	fi

## Show latest JMH Markdown report (if present)
show-jmh-report: ## Show path to JMH Markdown report
	@if [ -f target/jmh-report.md ]; then \
		echo "${GREEN}JMH Report:${RESET} file://$(shell pwd)/target/jmh-report.md"; \
	else \
		echo "${YELLOW}No JMH report found at target/jmh-report.md${RESET}"; \
	fi

########################################
# CI/CD targets (no redundant executions)
########################################

## Clean CI workspace
ci-clean:
	@echo "${GREEN}[CI] Cleaning workspace...${RESET}"
	rm -rf $(ARTIFACTS_DIR) target/ci-artifacts.zip || true
	mkdir -p $(ARTIFACTS_DIR) $(ART_UNIT_DIR) $(ART_PERF_DIR) $(ART_COV_DIR) $(ART_LOGS_DIR)

## Build only (no tests)
ci-build: ## Build project for CI (skip tests)
	@echo "${GREEN}[CI] Building project (skip tests)...${RESET}"
	mvn -DskipTests -DskipITs package

## Run unit tests only and collect reports
ci-test-unit: ## Run unit tests only and collect evidence
	@echo "${GREEN}[CI] Running unit tests...${RESET}"
	mvn -DexcludedGroups=integration test 2>&1 | tee $(ART_LOGS_DIR)/unit-tests.log
	@[ -d target/surefire-reports ] && cp -R target/surefire-reports/* $(ART_UNIT_DIR)/ || true

## Run performance tests (JMH) and collect logs
ci-test-perf: ## Run performance tests and collect evidence
	@echo "${GREEN}[CI] Running performance benchmarks...${RESET}"
	mvn -Pperf -DskipTests -DskipITs verify 2>&1 | tee $(ART_PERF_DIR)/benchmarks.log
	@[ -d target/benchmarks ] && cp -R target/benchmarks $(ART_PERF_DIR)/ || true

## Run faster performance tests (reduced iterations) and collect logs
ci-test-perf-fast: ## Run fast performance benchmarks and collect evidence
	@echo "${GREEN}[CI] Running fast performance benchmarks...${RESET}"
	mvn -Pperf-fast -DskipTests -DskipITs verify 2>&1 | tee $(ART_PERF_DIR)/benchmarks.log
	@[ -d target/benchmarks ] && cp -R target/benchmarks $(ART_PERF_DIR)/ || true

## Generate code coverage (reuse previous test run) and collect site
ci-coverage: ## Generate coverage report and collect evidence
	@echo "${GREEN}[CI] Generating coverage site from existing data...${RESET}"
	mvn -DskipTests jacoco:report 2>&1 | tee $(ART_LOGS_DIR)/coverage.log
	@[ -d $(JACOCO_SITE) ] && cp -R $(JACOCO_SITE)/* $(ART_COV_DIR)/ || true

## Fast full CI pipeline (reduced performance duration)
ci-all-fast: ci-clean ci-build ci-test-unit ci-test-perf-fast ci-coverage ci-artifacts ## Run full CI pipeline (fast)

## Full CI pipeline (no redundant test runs)
ci-all: ci-clean ci-build ci-test-unit ci-test-perf ci-coverage ci-artifacts ## Run full CI pipeline

## Package all CI artifacts into a zip
ci-artifacts: ## Package CI artifacts directory into a zip
	@echo "${GREEN}[CI] Packaging artifacts...${RESET}"
	@mkdir -p target
	@cd target && zip -qr ci-artifacts.zip ci-artifacts || true
	@echo "${GREEN}[CI] Package:${RESET} file://$(shell pwd)/target/ci-artifacts.zip"

## Show locations of performance and coverage outputs
reports: show-jmh-json show-jmh-report coverage ## Show JMH outputs and regenerate coverage site

## Check for dependency updates
dependency-updates: ## Check for dependency updates
	@echo "${GREEN}Checking for dependency updates...${RESET}"
	mvn versions:display-dependency-updates

## Show project information
info: ## Show project information
	@echo "${GREEN}Project Information:${RESET}"
	@echo "  Name: ${YELLOW}$(shell mvn help:evaluate -Dexpression=project.name -q -DforceStdout)${RESET}"
	@echo "  Version: ${YELLOW}$(shell mvn help:evaluate -Dexpression=project.version -q -DforceStdout)${RESET}"
	@echo "  Java Version: ${YELLOW}$(shell java -version 2>&1 | head -n 1)${RESET}"
	@echo "  Maven Version: ${YELLOW}$(shell mvn -v | head -n 1)${RESET}"
