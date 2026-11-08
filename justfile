# Just command runner for KMIP Adapter
# Run `just --list` to see all available commands

# Set default shell to bash for better script handling
set shell := ["bash", "-c"]

# Colors
GREEN := $(shell echo -e '\033[0;32m')
YELLOW := $(shell echo -e '\033[0;33m')
WHITE := $(shell echo -e '\033[1;37m')
RESET := $(shell echo -e '\033[0m')

# Default target when running just without arguments
default: help

# Run complete pipeline (build → tests → coverage → benchmark)
all: build test-unit coverage perf

# Show this help
help:
    #!/usr/bin/env bash
    echo "${WHITE}KMIP Adapter Development Commands:${RESET}"
    echo "  ${YELLOW}just install${RESET}      - Install project dependencies"
    echo "  ${YELLOW}just tests${RESET}         - Run all unit tests (alias for test-unit)"
    echo "  ${YELLOW}just test-unit${RESET}     - Run unit tests"
    echo "  ${YELLOW}just test-class TEST=...${RESET} - Run specific test class"
    echo "  ${YELLOW}just perf-runner${RESET}   - Run JMH using JmhBenchmarkRunner"
    echo "  ${YELLOW}just perf${RESET}          - Run performance benchmarks (perf profile)"
    echo "  ${YELLOW}just perf-fast${RESET}     - Run fast performance benchmarks (perf-fast profile)"
    echo "  ${YELLOW}just format${RESET}        - Format code using spotless (if configured)"
    echo "  ${YELLOW}just clean${RESET}         - Clean build artifacts"
    echo "  ${YELLOW}just build${RESET}         - Build the project (no implicit clean)"
    echo "  ${YELLOW}just run${RESET}           - Run the application (if Spring Boot plugin configured)"
    echo "  ${YELLOW}just coverage${RESET}      - Generate code coverage report"
    echo "  ${YELLOW}just show-jmh-json${RESET} - Show path to JMH JSON results"
    echo "  ${YELLOW}just show-jmh-report${RESET} - Show path to JMH Markdown report"

# Install project dependencies
install:
    @echo "📦 Installing dependencies..."
    mvn clean install -DskipTests

# Run all unit tests (alias for test-unit)
tests:
    @echo "${GREEN}Running all unit tests...${RESET}"
    @just test-unit

# Run unit tests
test-unit:
    @echo "${GREEN}Running unit tests...${RESET}"
    mvn -q test

# Run specific test class
test-class TEST:
    #!/usr/bin/env bash
    if [ -z "{{TEST}}" ]; then
        echo "${YELLOW}Please specify a test class with TEST=ClassName${RESET}"
        exit 1
    fi
    echo "${GREEN}Running test class: {{TEST}}${RESET}"
    mvn test -Dtest={{TEST}}

# Performance testing
perf-runner:
    @echo "${GREEN}Running performance benchmarks via runner...${RESET}"
    mvn -q -DskipTests test-compile exec:java -Dexec.mainClass="org.purplebean.kmip.benchmark.JmhBenchmarkRunner"

perf:
    @echo "${GREEN}Running performance benchmarks...${RESET}"
    mvn -q -DskipTests verify -P perf \
        -Dbench.threads=$$(nproc) \
        -Dbench.wi=3 \
        -Dbench.mi=5 \
        -Dbench.wt.ms=100 \
        -Dbench.mt.ms=200

perf-fast:
    @echo "${GREEN}Running fast performance benchmarks...${RESET}"
    mvn -q -DskipTests verify -P perf-fast \
        -Dbench.threads=$$(nproc) \
        -Dbench.wi=1 \
        -Dbench.mi=1 \
        -Dbench.wt.ms=50 \
        -Dbench.mt.ms=100

# Code formatting
format:
    @echo "${GREEN}Formatting code...${RESET}"
    @if grep -q "spotless-maven-plugin" pom.xml; then \
        echo "- Spotless detected. Running spotless:apply"; \
        mvn spotless:apply; \
    else \
        echo "- Spotless not configured in pom.xml. Skipping format."; \
    fi

# Build and clean
clean:
    @echo "${GREEN}Cleaning...${RESET}"
    mvn clean

build:
    @echo "${GREEN}Building project...${RESET}"
    @just install

# Run application
run:
    @echo "${GREEN}Running application...${RESET}"
    @if grep -q "spring-boot-maven-plugin" pom.xml; then \
        mvn spring-boot:run; \
    else \
        echo "${YELLOW}- Spring Boot plugin not configured in pom.xml. Nothing to run. Skipping.${RESET}"; \
    fi

# Code coverage and reports
coverage:
    @echo "${GREEN}Generating code coverage report from existing execution data...${RESET}"
    mvn -DskipTests jacoco:report
    @echo "${GREEN}Report generated at:${RESET} file://$(pwd)/target/site/jacoco/index.html"

show-jmh-json:
    @if [ -f target/jmh-results.json ]; then \
        echo "${GREEN}JMH JSON:${RESET} file://$(pwd)/target/jmh-results.json"; \
    else \
        echo "${YELLOW}No JMH JSON found at target/jmh-results.json${RESET}"; \
    fi

show-jmh-report:
    @if [ -f target/jmh-report.md ]; then \
        echo "${GREEN}JMH Report:${RESET} file://$(pwd)/target/jmh-report.md"; \
    else \
        echo "${YELLOW}No JMH report found at target/jmh-report.md${RESET}"; \
    fi

# Run performance benchmarks (alias for perf)
benchmark:
    @just perf

# Clean build artifacts
clean:
    @echo "${GREEN}Cleaning...${RESET}"
    mvn clean

# Build the project
build: install

# Run the application
run:
    @echo "${GREEN}Running application...${RESET}"
    @if grep -q "spring-boot-maven-plugin" pom.xml; then \
        mvn spring-boot:run; \
    else \
        echo "${YELLOW}- Spring Boot plugin not configured in pom.xml. Nothing to run. Skipping.${RESET}"; \
    fi
        mvn spring-boot:run
    else
        echo "- Spring Boot plugin not configured in pom.xml. Nothing to run. Skipping."
    fi

# Generate code coverage report
coverage:
    @echo "📊 Generating code coverage report (reusing exec data)..."
    mvn -DskipTests jacoco:report
    @echo "📄 Report generated at: target/site/jacoco/index.html"

# ==========================
# CI/CD tasks
# ==========================

ci-clean:
    #!/usr/bin/env bash
    echo "🧹 [CI] Cleaning workspace..."
    rm -rf target/ci-artifacts target/ci-artifacts.zip || true
    mkdir -p target/ci-artifacts/{unit,integration,performance,coverage,logs}

ci-build:
    @echo "🏗️ [CI] Building (skip tests)..."
    mvn -DskipTests -DskipITs package

ci-test-unit:
    #!/usr/bin/env bash
    echo "🧪 [CI] Unit tests..."
    mvn -DexcludedGroups=integration test 2>&1 | tee target/ci-artifacts/logs/unit-tests.log
    [ -d target/surefire-reports ] && cp -R target/surefire-reports/* target/ci-artifacts/unit/ || true

ci-test-integration:
    #!/usr/bin/env bash
    echo "🔍 [CI] Integration tests..."
    mvn -DskipTests -DskipITs=false failsafe:integration-test failsafe:verify 2>&1 | tee target/ci-artifacts/logs/integration-tests.log
    [ -d target/failsafe-reports ] && cp -R target/failsafe-reports/* target/ci-artifacts/integration/ || true

ci-test-perf:
    #!/usr/bin/env bash
    echo "⚡ [CI] Performance benchmarks..."
    mvn -Pperf -DskipTests -DskipITs verify 2>&1 | tee target/ci-artifacts/performance/benchmarks.log
    [ -d target/benchmarks ] && cp -R target/benchmarks target/ci-artifacts/performance/ || true

ci-test-perf-fast:
    #!/usr/bin/env bash
    echo "⚡ [CI] Fast performance benchmarks..."
    mvn -Pperf-fast -DskipTests -DskipITs verify 2>&1 | tee target/ci-artifacts/performance/benchmarks.log
    [ -d target/benchmarks ] && cp -R target/benchmarks target/ci-artifacts/performance/ || true

ci-coverage:
    #!/usr/bin/env bash
    echo "📊 [CI] Coverage site..."
    mvn -DskipTests jacoco:report 2>&1 | tee target/ci-artifacts/logs/coverage.log
    [ -d target/site/jacoco ] && cp -R target/site/jacoco/* target/ci-artifacts/coverage/ || true

ci-report:
    #!/usr/bin/env bash
    REPORT=target/ci-artifacts/summary.md
    ART_UNIT_DIR=target/ci-artifacts/unit
    ART_IT_DIR=target/ci-artifacts/integration
    ART_PERF_DIR=target/ci-artifacts/performance
    ART_COV_DIR=target/ci-artifacts/coverage
    RUN_U=$(grep -ho 'tests="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    FAIL_U=$(grep -ho 'failures="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    ERR_U=$(grep -ho 'errors="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    SKIP_U=$(grep -ho 'skipped="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    RUN_I=$(grep -ho 'tests="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    FAIL_I=$(grep -ho 'failures="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    ERR_I=$(grep -ho 'errors="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    SKIP_I=$(grep -ho 'skipped="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    COV=$( [ -f "$ART_COV_DIR"/jacoco.csv ] && tail -n +2 "$ART_COV_DIR"/jacoco.csv | head -1 | cut -d, -f4 | xargs printf "%.1f%%" || echo "0%" )
    PERF=$( [ -s "$ART_PERF_DIR"/benchmarks.log ] && echo "✅ Generated" || echo "⏳ Not run" )
    {
      echo "# CI Evidence Summary"; echo; echo "Generated: $(date)"; echo;
      echo "## Unit Tests"; STATUS_U=$( [ "$FAIL_U" = "0" ] && [ "$ERR_U" = "0" ] && echo "✅ PASSED" || echo "❌ FAILED" );
      echo "- Status: $STATUS_U"; echo "- Tests Run: $RUN_U | Failures: $FAIL_U | Errors: $ERR_U | Skipped: $SKIP_U"; echo;
      if [ "$RUN_I" -gt 0 ]; then
        echo "## Integration Tests"; 
        STATUS_I=$( [ "$FAIL_I" = "0" ] && [ "$ERR_I" = "0" ] && echo "✅ PASSED" || echo "❌ FAILED" );
        echo "- Status: $STATUS_I"; 
        echo "- Tests Run: $RUN_I | Failures: $FAIL_I | Errors: $ERR_I | Skipped: $SKIP_I"; 
      else
        echo "<!-- ## Integration Tests (no tests found) -->";
      fi; 
      echo;
      echo "## Performance Tests"; echo "- Status: $PERF"; echo "- Log: target/ci-artifacts/performance/benchmarks.log"; echo;
      echo "## Code Coverage"; echo "- Status: $( [ -f "$ART_COV_DIR"/index.html ] && echo "✅ Generated" || echo "⏳ Not generated" )";
      echo "- Overall Coverage: $COV"; echo "- Report: target/ci-artifacts/coverage/index.html"; echo;
      echo "## Artifacts"; echo "- Unit: target/ci-artifacts/unit"; echo "- Integration: target/ci-artifacts/integration";
      echo "- Performance: target/ci-artifacts/performance"; echo "- Coverage: target/ci-artifacts/coverage";
    } > "$REPORT"
    cat "$REPORT"

ci-report-json:
    #!/usr/bin/env bash
    JSON=target/ci-artifacts/summary.json
    ART_UNIT_DIR=target/ci-artifacts/unit
    ART_IT_DIR=target/ci-artifacts/integration
    ART_PERF_DIR=target/ci-artifacts/performance
    ART_COV_DIR=target/ci-artifacts/coverage
    RUN_U=$(grep -ho 'tests="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    FAIL_U=$(grep -ho 'failures="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    ERR_U=$(grep -ho 'errors="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    SKIP_U=$(grep -ho 'skipped="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    RUN_I=$(grep -ho 'tests="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    FAIL_I=$(grep -ho 'failures="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    ERR_I=$(grep -ho 'errors="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    SKIP_I=$(grep -ho 'skipped="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    COV=$( [ -f "$ART_COV_DIR"/jacoco.csv ] && tail -n +2 "$ART_COV_DIR"/jacoco.csv | head -1 | cut -d, -f4 | xargs printf "%.1f" || echo 0 )
    PERF=$( [ -s "$ART_PERF_DIR"/benchmarks.log ] && echo true || echo false )
    {
      echo "{";
      echo "  \"generated\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",";
      echo "  \"unit\": { \"run\": $RUN_U, \"failures\": $FAIL_U, \"errors\": $ERR_U, \"skipped\": $SKIP_U },";
      echo "  \"integration\": { \"run\": $RUN_I, \"failures\": $FAIL_I, \"errors\": $ERR_I, \"skipped\": $SKIP_I },";
      echo "  \"performance\": { \"generated\": $PERF, \"log\": \"target/ci-artifacts/performance/benchmarks.log\" },";
      echo "  \"coverage\": { \"overall\": $COV, \"report\": \"target/ci-artifacts/coverage/index.html\" }";
      echo "}";
    } > "$JSON"
    cat "$JSON"

ci-docs:
    #!/usr/bin/env bash
    OUT=docs/03-guides/testing/reports.md
    ART_UNIT_DIR=target/ci-artifacts/unit
    ART_IT_DIR=target/ci-artifacts/integration
    ART_PERF_DIR=target/ci-artifacts/performance
    ART_COV_DIR=target/ci-artifacts/coverage
    RUN_U=$(grep -ho 'tests="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    FAIL_U=$(grep -ho 'failures="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    ERR_U=$(grep -ho 'errors="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    SKIP_U=$(grep -ho 'skipped="[0-9]\+"' "$ART_UNIT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    RUN_I=$(grep -ho 'tests="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    FAIL_I=$(grep -ho 'failures="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    ERR_I=$(grep -ho 'errors="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    SKIP_I=$(grep -ho 'skipped="[0-9]\+"' "$ART_IT_DIR"/*.xml 2>/dev/null | grep -o '[0-9]\+' | awk '{s+=$$1} END {print s+0}')
    COV=$( [ -f "$ART_COV_DIR"/jacoco.csv ] && tail -n +2 "$ART_COV_DIR"/jacoco.csv | head -1 | cut -d, -f4 | xargs printf "%.1f%%" || echo "0%" )
    PERF=$( [ -s "$ART_PERF_DIR"/benchmarks.log ] && echo "✅ Generated" || echo "⏳ Not run" )
    {
      echo "# Test Reports and Coverage"; echo; echo "## Latest Test Results"; echo; echo "Generated: $(date)"; echo;
      echo "### Unit Tests"; STATUS_U=$( [ "$FAIL_U" = "0" ] && [ "$ERR_U" = "0" ] && echo "✅ PASSED" || echo "❌ FAILED" );
      echo "- **Status**: $STATUS_U"; echo "- **Tests Run**: $RUN_U"; echo "- **Failures**: $FAIL_U"; echo "- **Errors**: $ERR_U"; echo "- **Skipped**: $SKIP_U";
      echo "- **Reports**: [Surefire XML](../../../target/ci-artifacts/unit/)"; echo;
      if [ "$RUN_I" -gt 0 ]; then
        echo "### Integration Tests"; 
        STATUS_I=$( [ "$FAIL_I" = "0" ] && [ "$ERR_I" = "0" ] && echo "✅ PASSED" || echo "❌ FAILED" );
        echo "- **Status**: $STATUS_I"; 
        echo "- **Tests Run**: $RUN_I"; 
        echo "- **Failures**: $FAIL_I"; 
        echo "- **Errors**: $ERR_I"; 
        echo "- **Skipped**: $SKIP_I";
        echo "- **Reports**: [Failsafe XML](../../../target/ci-artifacts/integration/)"; 
      else
        echo "<!-- ### Integration Tests (no tests found) -->";
      fi;
      echo;
      echo "### Performance Tests"; echo "- **Status**: $PERF"; echo "- **Log**: [benchmarks.log](../../../target/ci-artifacts/performance/benchmarks.log)"; echo;
      echo "### Code Coverage"; echo "- **Status**: $( [ -f "$ART_COV_DIR"/index.html ] && echo "✅ Generated" || echo "⏳ Not generated" )";
      echo "- **Overall Coverage**: $COV"; echo "- **Report**: [index.html](../../../target/ci-artifacts/coverage/index.html)"; echo;
      echo "## Report Locations"; \
      echo "- **Unit Reports**: [../../../target/ci-artifacts/unit/](../../../target/ci-artifacts/unit/)"; \
      echo "- **Integration Reports**: [../../../target/ci-artifacts/integration/](../../../target/ci-artifacts/integration/)"; \
      echo "- **Coverage Reports**: [../../../target/ci-artifacts/coverage/](../../../target/ci-artifacts/coverage/)"; \
      echo "- **Performance Logs**: [../../../target/ci-artifacts/performance/](../../../target/ci-artifacts/performance/)"; \
    } > "$OUT"
    echo "Updated: $OUT"

ci-artifacts:
    #!/usr/bin/env bash
    cd target && zip -qr ci-artifacts.zip ci-artifacts || true
    echo "Package: target/ci-artifacts.zip"

ci-all:
    @just ci-clean ci-build ci-test-unit ci-test-integration ci-test-perf ci-coverage ci-report ci-report-json ci-docs ci-artifacts

ci-all-fast:
    @just ci-clean ci-build ci-test-unit ci-test-integration ci-test-perf-fast ci-coverage ci-report ci-report-json ci-docs ci-artifacts

# Show project information
info:
    @echo "📋 Project Information:"
    @echo "  Name: $(mvn help:evaluate -Dexpression=project.name -q -DforceStdout)"
    @echo "  Version: $(mvn help:evaluate -Dexpression=project.version -q -DforceStdout)"
    @echo "  Java Version: $(java -version 2>&1 | head -n 1)"
    @echo "  Maven Version: $(mvn -v | head -n 1)"
