#!/bin/bash
# CODING API - biaopin-swiftagent 项目迭代查询
# 用法: ./coding-swiftagent.sh [iterations|issues|all]

API_URL="https://digit-force.coding.net/open-api/?Action=DescribeIssueList&action=DescribeIssueList"
TOKEN="ee3ef032e2b38621a6d701090fc6166d808dc7df"
PROJECT_NAME="biaopin-swiftagent"

# 默认查询20条
LIMIT=${LIMIT:-20}

curl -s --location "$API_URL" \
  --header 'Accept: application/json' \
  --header "Authorization: token $TOKEN" \
  --header 'Content-Type: application/json' \
  --data "{
    \"ProjectName\": \"$PROJECT_NAME\",
    \"IssueType\": \"ALL\",
    \"Offset\": \"0\",
    \"Limit\": \"$LIMIT\",
    \"Conditions\": [],
    \"SortKey\": \"CODE\",
    \"SortValue\": \"DESC\"
  }"
