"""
Central configuration — all matching criteria and constants live here.
"""

TARGET_STATES = ["Florida", "Texas", "North Carolina"]
STATE_ABBREVIATIONS = ["FL", "TX", "NC"]
STATE_CITIES = {
    "Florida": ["Miami", "Orlando", "Tampa", "Jacksonville", "Tallahassee", "Fort Lauderdale", "St. Petersburg"],
    "Texas": ["Houston", "Dallas", "Austin", "San Antonio", "Fort Worth", "El Paso", "Arlington"],
    "North Carolina": ["Charlotte", "Raleigh", "Greensboro", "Durham", "Winston-Salem", "Fayetteville", "Cary"],
}

TARGET_JOB_TITLES = [
    "GIS Analyst",
    "GIS Specialist",
    "GIS Technician",
    "Spatial Data Analyst",
    "Spatial Analyst",
    "Geospatial Analyst",
    "Geospatial Developer",
    "Remote Sensing Analyst",
    "GIS Developer",
    "GIS Engineer",
    "GIS Project Manager",
    "GIS Coordinator",
    "Environmental GIS Analyst",
    "Transportation GIS Analyst",
    "GIS Database Analyst",
    "Cartographer",
    "Mapping Specialist",
    "Spatial Data Scientist",
    "Location Intelligence Analyst",
    "GIS Intern",
]

# Keywords weighted by relevance to resume
HIGH_VALUE_KEYWORDS = {
    # Core GIS (weight 3)
    "arcgis pro": 3,
    "arcgis": 3,
    "qgis": 3,
    "esri": 3,
    "gis analyst": 3,
    "gis specialist": 3,
    "gis technician": 3,
    "geospatial": 3,
    "spatial analysis": 3,
    "gis developer": 3,
    "gis engineer": 3,

    # Programming (weight 2)
    "python": 2,
    "sql": 2,
    "postgis": 2,
    "geopandas": 2,
    "javascript": 2,
    "leaflet": 2,
    "d3.js": 2,
    "d3": 2,
    "html": 2,
    "css": 2,

    # GIS domain (weight 2)
    "remote sensing": 2,
    "cartography": 2,
    "lidar": 2,
    "network analysis": 2,
    "geocoding": 2,
    "geodatabase": 2,
    "web mapping": 2,
    "spatial data": 2,
    "mapping": 2,
    "feature class": 2,
    "shapefile": 2,
    "raster": 2,
    "vector": 2,
    "coordinate system": 2,
    "projection": 2,
    "topology": 2,

    # Tools (weight 1)
    "autocad": 1,
    "cad": 1,
    "smallworld": 1,
    "google earth engine": 1,
    "arcpy": 1,
    "model builder": 1,
    "modelbuilder": 1,
    "arcgis online": 1,
    "agol": 1,
    "mapbox": 1,
    "maplibre": 1,
    "tableau": 1,
    "power bi": 1,
    "aws": 1,
    "streamlit": 1,

    # Domain areas (weight 1)
    "environmental": 1,
    "transportation": 1,
    "utilities": 1,
    "utility": 1,
    "planning": 1,
    "infrastructure": 1,
    "surveying": 1,
    "survey": 1,
    "civil engineering": 1,
    "stormwater": 1,
    "land use": 1,
    "land management": 1,
    "public health": 1,
    "risk analysis": 1,
    "data visualization": 1,
    "map": 1,
}

# Reduce score for roles that are over-qualified or require clearance
NEGATIVE_KEYWORDS = [
    "senior",
    "lead",
    "principal",
    "director",
    "vice president",
    "vp",
    "10+ years",
    "10 years",
    "8+ years",
    "8 years",
    "7+ years",
    "7 years",
    "security clearance required",
    "active clearance",
    "ts/sci",
    "top secret",
    "phd required",
    "doctorate required",
]

# Score thresholds
MIN_SCORE_TO_INCLUDE = 40
MAX_RESULTS_PER_EMAIL = 15

# Seen-jobs deduplication cache
SEEN_JOBS_PATH = "data/seen_jobs.json"
SEEN_JOBS_MAX_AGE_DAYS = 30

# Email
EMAIL_SUBJECT_PREFIX = "GIS Job Alert"
