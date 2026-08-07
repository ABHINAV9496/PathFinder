REJECT_ROLE_KEYWORDS = {
    "data analyst", "business analyst", "java developer", "frontend developer",
    "qa engineer", "quality assurance", "devops engineer", "site reliability",
    "full stack developer", "fullstack developer",
    ".net developer", "dotnet developer", "dot net developer",
    "laravel developer", "php developer", "node.js developer", "nodejs developer",
    "angular developer", "vue developer", "flutter developer", "android developer",
    "ios developer", "swift developer", "kotlin developer",
    "salesforce", "service now", "servicenow",
    "project manager", "scrum master", "product manager",
    "business development", "marketing", "sales",
    "ui/ux", "ui ux", "graphic designer",
    "mechanical engineer", "civil engineer", "electrical engineer",
    "embedded engineer", "hardware engineer",
    "oracle developer", "sap developer",
    "react native", "ionic developer",
    "rails developer", "ruby developer",
    "golang developer", "go developer", "rust developer",
    "c++ developer", "c developer",
    "data engineer", "data scientist", "ml engineer",
    "cyber security", "network engineer", "system administrator",
    "technical support", "it support", "help desk",
    "trainee", "intern", "fresher",
}

RECRUITER_KEYWORDS = {
    "recruitment", "recruiting", "talent", "staffing", "humanresources",
    "hrconsulting", "jobs", "careers", "hiring", "consulting",
    "headhunter", "placement", "premiumhumanresources", "recruiter",
}

FREE_EMAILS = {
    "gmail.com", "yahoo.com", "hotmail.com", "outlook.com",
    "mail.com", "protonmail.com", "aol.com", "zoho.com",
    "yandex.com", "gmx.com", "icloud.com",
}

NORTH_INDIA_STATES = [
    "delhi", "noida", "gurgaon", "gurugram", "faridabad", "ghaziabad",
    "udaipur", "jaipur", "jodhpur", "kota", "ajmer",
    "lucknow", "kanpur", "agra", "varanasi", "meerut", "prayagraj",
    "chandigarh", "ludhiana", "amritsar", "jalandhar", "patiala",
    "bhopal", "indore", "jabalpur", "gwalior",
    "patna", "raipur", "ranchi", "dehradun", "shimla",
    "ahmedabad", "surat", "rajkot", "vadodara",
    "jharkhand", "chhattisgarh", "madhya pradesh", "uttar pradesh",
    "haryana", "punjab", "rajasthan", "uttarakhand", "bihar", "gujarat",
    "himachal", "jammu", "kashmir",
]

# General-purpose vocabulary of skills seen across job descriptions.
# Used to compute skill gaps for ANY profession (not just software).
COMMON_JD_SKILLS = {
    # software / data
    "python", "django", "drf", "flask", "fastapi", "node.js", "nodejs",
    "java", "c++", "c#", "go", "golang", "rust", "scala", "ruby", "php",
    "javascript", "typescript", "react", "react.js", "vue", "angular",
    "graphql", "grpc", "microservices", "rest api", "kafka", "rabbitmq",
    "elasticsearch", "solr", "spark", "hadoop", "airflow", "mongodb",
    "cassandra", "dynamodb", "neo4j", "mysql", "postgresql", "redis",
    "sql", "etl", "datalake", "data warehouse", "tableau", "power bi",
    "looker", "pandas", "numpy", "machine learning", "deep learning",
    "nlp", "llm", "prompt engineering", "computer vision", "mlops",
    # cloud / infra
    "aws", "ec2", "s3", "rds", "lambda", "gcp", "google cloud", "azure",
    "kubernetes", "k8s", "docker", "terraform", "ci/cd", "jenkins",
    "github actions", "linux", "nginx", "git",
    # quality / testing
    "selenium", "cypress", "playwright", "jest", "pytest", "junit",
    "qa", "test automation",
    # design / creative
    "figma", "photoshop", "illustrator", "adobe xd", "sketch", "indesign",
    "after effects", "premiere pro", "canva", "ux research", "wireframing",
    "prototyping", "user testing", "design systems", "brand identity",
    # marketing / growth
    "seo", "sem", "content marketing", "email marketing", "social media",
    "google analytics", "google ads", "meta ads", "crm", "copywriting",
    "a/b testing", "growth hacking", "influencer marketing",
    # business / operations
    "excel", "powerpoint", "google sheets", "salesforce", "hubspot",
    "project management", "agile", "scrum", "jira", "slack", "notion",
    "lead generation", "negotiation", "presentation", "data analysis",
    # security / ops
    "cyber security", "penetration testing", "firewall", "soc",
    # mobile / other tech
    "flutter", "swift", "kotlin", "android", "ios", "react native",
    "blockchain", "web3", "solidity", "unity", "unreal engine",
    "wordpress", "shopify", "woocommerce",
}
