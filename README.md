# pypo - Ontology-driven FastAPI Service

온톨로지(Ontology) 지식 그래프 기반의 데이터 모델링 및 지식 추론을 제공하는 FastAPI 애플리케이션입니다.
복잡한 도메인 엔티티 관계를 서술하고, SPARQL 및 추론 엔진을 활용한 고도화된 지식 검색 API를 제공합니다.

## Project Overview

- **목적**: 도메인 엔티티 간의 관계 정의 및 OWL/RDF 기반 지식 추론 API 구축
- **주요 특징**:
  - **지식 그래프 엔진 연결**: SPARQL Endpoint 연동을 통한 유연한 데이터 그래프 조회
  - **온톨로지 추론(Reasoning)**: 규칙 기반 관계 추론 및 숨겨진 지식 추출
  - **FastAPI & Pydantic**: 온톨로지 데이터와 REST API 응답 객체 간의 타입 안전한 매핑

## Tech Stack

- **Framework**: FastAPI (Python 3.13+)
- **Data & Ontology Engine**:
  - **Triple Store / Graph DB**: GraphDB / Stardog / Apache Jena / Neo4j
  - **Ontology Library**: `rdflib`, `owlready2`
  - **Query Language**: SPARQL 1.1
- **Validation & Data Mapping**: Pydantic v2
- **Package Manager**: uv / poetry
