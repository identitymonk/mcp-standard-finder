// WIMSE Active Drafts Graph Database Representation
// Neo4j Cypher Query Language

// Create Draft Documents
CREATE (arch:Draft {name: "draft-ietf-wimse-arch", title: "WIMSE Architecture", type: "foundational"})
CREATE (s2s:Draft {name: "draft-ietf-wimse-s2s-protocol", title: "Workload to Workload Authentication", type: "protocol"})
CREATE (bcp:Draft {name: "draft-ietf-wimse-workload-identity-bcp", title: "OAuth 2.0 Client Assertion in Workload Environments", type: "best_practices"})
CREATE (practices:Draft {name: "draft-ietf-wimse-workload-identity-practices", title: "Workload Identity Practices", type: "informational"})

// Core Concepts
CREATE (workload:Concept {name: "Workload", definition: "Running instance of software executing for a specific purpose"})
CREATE (identity:Concept {name: "Workload Identity", definition: "Identity representation for workloads"})
CREATE (trustDomain:Concept {name: "Trust Domain", definition: "Security boundary for workload identity"})
CREATE (credentials:Concept {name: "Workload Identity Credentials", definition: "Cryptographic proof of workload identity"})
CREATE (context:Concept {name: "Security Context", definition: "Contextual security information"})

// Authentication & Authorization
CREATE (auth:Concept {name: "Authentication", definition: "Verification of workload identity"})
CREATE (authz:Concept {name: "Authorization", definition: "Access control for workloads"})
CREATE (wit:Token {name: "Workload Identity Token", type: "JWT", purpose: "identity_assertion"})
CREATE (proof:Token {name: "Proof Token", type: "JWT", purpose: "proof_of_possession"})

// Protocols & Standards
CREATE (oauth:Protocol {name: "OAuth 2.0", type: "authorization_framework"})
CREATE (jwt:Protocol {name: "JWT", type: "token_format"})
CREATE (mtls:Protocol {name: "Mutual TLS", type: "transport_security"})
CREATE (http:Protocol {name: "HTTP", type: "application_protocol"})
CREATE (dpop:Protocol {name: "DPoP", type: "proof_of_possession"})
CREATE (msgSig:Protocol {name: "HTTP Message Signatures", type: "message_authentication"})

// Platforms & Environments
CREATE (k8s:Platform {name: "Kubernetes", type: "container_orchestration"})
CREATE (spiffe:Platform {name: "SPIFFE", type: "identity_framework"})
CREATE (cloud:Platform {name: "Cloud Providers", type: "cloud_platform"})
CREATE (cicd:Platform {name: "CI/CD Systems", type: "deployment_platform"})

// Use Cases
CREATE (bootstrap:UseCase {name: "Bootstrapping", description: "Initial credential provisioning"})
CREATE (serviceAuth:UseCase {name: "Service Authentication", description: "Workload-to-workload authentication"})
CREATE (delegation:UseCase {name: "Delegation", description: "Identity delegation and impersonation"})
CREATE (audit:UseCase {name: "Audit Trails", description: "Security auditing and logging"})
CREATE (crossDomain:UseCase {name: "Cross-Domain Communication", description: "Inter-domain workload communication"})

// Security Considerations
CREATE (interception:Threat {name: "Traffic Interception", type: "network_attack"})
CREATE (disclosure:Threat {name: "Information Disclosure", type: "data_leak"})
CREATE (credTheft:Threat {name: "Credential Theft", type: "credential_compromise"})
CREATE (compromise:Threat {name: "Workload Compromise", type: "system_compromise"})

// Document Relationships
CREATE (arch)-[:DEFINES]->(workload)
CREATE (arch)-[:DEFINES]->(identity)
CREATE (arch)-[:DEFINES]->(trustDomain)
CREATE (arch)-[:DEFINES]->(credentials)
CREATE (arch)-[:DEFINES]->(context)

CREATE (s2s)-[:IMPLEMENTS]->(arch)
CREATE (s2s)-[:DEFINES]->(wit)
CREATE (s2s)-[:DEFINES]->(proof)
CREATE (s2s)-[:USES]->(jwt)
CREATE (s2s)-[:USES]->(mtls)
CREATE (s2s)-[:USES]->(http)
CREATE (s2s)-[:SUPPORTS]->(dpop)
CREATE (s2s)-[:SUPPORTS]->(msgSig)

CREATE (bcp)-[:IMPLEMENTS]->(arch)
CREATE (bcp)-[:USES]->(oauth)
CREATE (bcp)-[:USES]->(jwt)
CREATE (bcp)-[:ADDRESSES]->(k8s)
CREATE (bcp)-[:ADDRESSES]->(spiffe)
CREATE (bcp)-[:ADDRESSES]->(cloud)
CREATE (bcp)-[:ADDRESSES]->(cicd)

CREATE (practices)-[:REFERENCES]->(arch)
CREATE (practices)-[:DESCRIBES]->(k8s)
CREATE (practices)-[:DESCRIBES]->(spiffe)
CREATE (practices)-[:DESCRIBES]->(cloud)

// Concept Relationships
CREATE (workload)-[:HAS]->(identity)
CREATE (identity)-[:WITHIN]->(trustDomain)
CREATE (identity)-[:PROVEN_BY]->(credentials)
CREATE (credentials)-[:ENCODED_AS]->(jwt)
CREATE (identity)-[:REQUIRES]->(auth)
CREATE (auth)-[:ENABLES]->(authz)

CREATE (wit)-[:REPRESENTS]->(identity)
CREATE (proof)-[:PROVES]->(credentials)
CREATE (wit)-[:COMBINED_WITH]->(proof)

// Protocol Relationships
CREATE (oauth)-[:USES]->(jwt)
CREATE (mtls)-[:PROVIDES]->(auth)
CREATE (http)-[:CARRIES]->(wit)
CREATE (http)-[:CARRIES]->(proof)
CREATE (dpop)-[:EXTENDS]->(oauth)
CREATE (msgSig)-[:SECURES]->(http)

// Use Case Relationships
CREATE (bootstrap)-[:CREATES]->(credentials)
CREATE (serviceAuth)-[:USES]->(wit)
CREATE (serviceAuth)-[:USES]->(proof)
CREATE (delegation)-[:EXTENDS]->(identity)
CREATE (audit)-[:TRACKS]->(identity)
CREATE (crossDomain)-[:SPANS]->(trustDomain)

// Platform Relationships
CREATE (k8s)-[:PROVIDES]->(workload)
CREATE (spiffe)-[:PROVIDES]->(identity)
CREATE (cloud)-[:HOSTS]->(workload)
CREATE (cicd)-[:DEPLOYS]->(workload)

// Security Relationships
CREATE (interception)-[:THREATENS]->(wit)
CREATE (disclosure)-[:THREATENS]->(context)
CREATE (credTheft)-[:THREATENS]->(credentials)
CREATE (compromise)-[:THREATENS]->(workload)

CREATE (mtls)-[:MITIGATES]->(interception)
CREATE (proof)-[:MITIGATES]->(credTheft)
CREATE (auth)-[:MITIGATES]->(compromise)

// Cross-Draft Dependencies
CREATE (s2s)-[:DEPENDS_ON]->(arch)
CREATE (bcp)-[:DEPENDS_ON]->(arch)
CREATE (practices)-[:INFORMS]->(bcp)
CREATE (s2s)-[:COMPLEMENTS]->(bcp)

// Query Examples:
// Find all concepts defined by architecture draft:
// MATCH (arch:Draft {name: "draft-ietf-wimse-arch"})-[:DEFINES]->(concept) RETURN concept

// Find protocols used by S2S draft:
// MATCH (s2s:Draft {name: "draft-ietf-wimse-s2s-protocol"})-[:USES]->(protocol) RETURN protocol

// Find security threats and their mitigations:
// MATCH (threat:Threat)<-[:MITIGATES]-(mitigation) RETURN threat, mitigation

// Find platform support across drafts:
// MATCH (draft:Draft)-[:ADDRESSES|DESCRIBES]->(platform:Platform) RETURN draft, platform
