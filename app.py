from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from google import genai
import json, re, math, time
import threading   


app = Flask(__name__, static_folder=".")
CORS(app)

# ── API Key Rotation (add more keys to beat daily quota) 

GEMINI_KEYS = [
    "AIzaSyDjEcY2ODs3u6SFddv_UGvNinNECpgY5Vg",   # key 1
    "AIzaSyA1Uxth5nhqoQkfvbEVPoIbecxBysFebhU",   # key 2
    "AIzaSyBnimWXCuf3jBdMV3sidmRJzYfQfj0xLJw" #     key3
]
_key_index = 0
_key_lock = threading.Lock()

def get_client():
    """Return current Gemini client."""
    return genai.Client(api_key=GEMINI_KEYS[_key_index])

def rotate_key():
    """Switch to next API key."""
    global _key_index
    with _key_lock:
        _key_index = (_key_index + 1) % len(GEMINI_KEYS)
        print(f"  [Key rotation] switched to key #{_key_index + 1}")

# ── Rate-limit fix: retry with backoff ───────────────────────────
import threading
_last_call = 0.0
_call_lock = threading.Lock()
MIN_INTERVAL = 4.0  # seconds between Gemini calls (free tier: ~15 RPM)

def gemini_call(prompt, model="gemini-1.5-flash"):
    """Call Gemini with rate limiting, key rotation, and exponential backoff."""
    global _last_call

    # Enforce minimum interval between calls
    with _call_lock:
        now = time.time()
        wait = MIN_INTERVAL - (now - _last_call)
        if wait > 0:
            time.sleep(wait)
        _last_call = time.time()

    last_err = None
    for attempt in range(len(GEMINI_KEYS) * 3):  # try all keys up to 3x each
        try:
            client = get_client()
            resp = client.models.generate_content(model=model, contents=prompt)
            return resp.text or ""
        except Exception as ex:
            last_err = ex
            msg = str(ex).lower()
            if "429" in msg or "quota" in msg or "rate" in msg or "exhausted" in msg:
                print(f"  [429] Key #{_key_index+1} rate limited. Rotating key...")
                rotate_key()
                wait_time = min(5 * (attempt + 1), 30)
                print(f"  Waiting {wait_time}s before retry (attempt {attempt+1})...")
                time.sleep(wait_time)
            elif "400" in msg or "invalid_argument" in msg:
                raise Exception(f"Bad request — check your prompt: {ex}")
            elif "401" in msg or "api_key" in msg or "unauthorized" in msg:
                print(f"  [Invalid key] Key #{_key_index+1} rejected. Rotating...")
                rotate_key()
                time.sleep(1)
            else:
                time.sleep(2)
                if attempt >= 2:
                    raise

    raise Exception(
        "All Gemini API keys are rate limited (429). Options:\n"
        "1. Wait until midnight Pacific Time for quota reset\n"
        "2. Add more free keys at https://aistudio.google.com/app/apikey\n"
        "3. Upgrade to Gemini paid plan for higher limits"
    )


# ── Course data ───────────────────────────────────────────────────
COURSES = [
    {"id":1,"title":"Python for Everybody Specialization","platform":"Coursera","category":"Programming","level":"Beginner","rating":4.8,"price":0,"hours":30,"url":"https://www.coursera.org/specializations/python","skills":["Python","Variables","Loops","Functions","APIs","Files"]},
    {"id":2,"title":"CS50: Introduction to Computer Science","platform":"edX","category":"Programming","level":"Beginner","rating":4.9,"price":0,"hours":60,"url":"https://cs50.harvard.edu/x/","skills":["C","Python","SQL","Algorithms","Problem Solving","Web"]},
    {"id":3,"title":"JavaScript Algorithms & Data Structures","platform":"freeCodeCamp","category":"Programming","level":"Intermediate","rating":4.7,"price":0,"hours":40,"url":"https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures/","skills":["JavaScript","Algorithms","Data Structures","ES6","OOP","Regex"]},
    {"id":4,"title":"100 Days of Code – Python Bootcamp","platform":"Udemy","category":"Programming","level":"Beginner","rating":4.7,"price":15,"hours":55,"url":"https://www.udemy.com/course/100-days-of-code/","skills":["Python","Automation","Web Scraping","APIs","Games","GUI"]},
    {"id":5,"title":"C++ Programming: Beginner to Beyond","platform":"Udemy","category":"Programming","level":"Advanced","rating":4.6,"price":13,"hours":46,"url":"https://www.udemy.com/course/beginning-c-plus-plus-programming/","skills":["C++","OOP","Memory Management","STL","Concurrency","Templates"]},
    {"id":6,"title":"Java Programming & Software Engineering","platform":"Coursera","category":"Programming","level":"Beginner","rating":4.7,"price":0,"hours":45,"url":"https://www.coursera.org/specializations/java-programming","skills":["Java","OOP","Data Structures","Algorithms","Software Design"]},
    {"id":7,"title":"Rust Programming – Official Book","platform":"rust-lang.org","category":"Programming","level":"Intermediate","rating":4.8,"price":0,"hours":25,"url":"https://doc.rust-lang.org/book/","skills":["Rust","Memory Safety","Concurrency","Systems Programming","WebAssembly"]},
    {"id":8,"title":"Go Programming Language Tour","platform":"go.dev","category":"Programming","level":"Beginner","rating":4.7,"price":0,"hours":10,"url":"https://go.dev/tour/welcome/1","skills":["Go","Goroutines","Channels","Interfaces","Packages"]},
    {"id":9,"title":"MIT: Introduction to Algorithms","platform":"MIT OpenCourseWare","category":"Programming","level":"Advanced","rating":4.9,"price":0,"hours":80,"url":"https://ocw.mit.edu/courses/6-006-introduction-to-algorithms-fall-2011/","skills":["Algorithms","Dynamic Programming","Graph Theory","Sorting","Complexity"]},
    {"id":10,"title":"Kotlin for Java Developers","platform":"Coursera","category":"Programming","level":"Intermediate","rating":4.6,"price":0,"hours":20,"url":"https://www.coursera.org/learn/kotlin-for-java-developers","skills":["Kotlin","Coroutines","Null Safety","Functional Programming","Android"]},
    {"id":11,"title":"The Complete Web Development Bootcamp","platform":"Udemy","category":"Web Dev","level":"Beginner","rating":4.7,"price":15,"hours":65,"url":"https://www.udemy.com/course/the-complete-web-development-bootcamp/","skills":["HTML","CSS","JavaScript","React","Node.js","MongoDB","Express"]},
    {"id":12,"title":"Full Stack Open 2024","platform":"University of Helsinki","category":"Web Dev","level":"Intermediate","rating":4.8,"price":0,"hours":70,"url":"https://fullstackopen.com/en/","skills":["React","Node.js","REST","GraphQL","TypeScript","Testing","Redux"]},
    {"id":13,"title":"The Odin Project – Full Stack JavaScript","platform":"The Odin Project","category":"Web Dev","level":"Beginner","rating":4.9,"price":0,"hours":80,"url":"https://www.theodinproject.com/paths/full-stack-javascript","skills":["HTML","CSS","JavaScript","React","Node","Databases","Git"]},
    {"id":14,"title":"Next.js 14 & React – Complete Guide","platform":"Udemy","category":"Web Dev","level":"Intermediate","rating":4.7,"price":13,"hours":25,"url":"https://www.udemy.com/course/nextjs-react-the-complete-guide/","skills":["Next.js","React","SSR","API Routes","Deployment","Auth"]},
    {"id":15,"title":"CSS – Flexbox, Grid & Sass Complete Guide","platform":"Udemy","category":"Web Dev","level":"Beginner","rating":4.6,"price":13,"hours":23,"url":"https://www.udemy.com/course/css-the-complete-guide-incl-flexbox-grid-sass/","skills":["CSS","Flexbox","Grid","Sass","Animations","Responsive Design"]},
    {"id":16,"title":"Django Full Course – Python Web Dev","platform":"freeCodeCamp","category":"Web Dev","level":"Intermediate","rating":4.6,"price":0,"hours":18,"url":"https://www.youtube.com/watch?v=o0XbHvKxw7Y","skills":["Python","Django","ORM","Authentication","REST APIs","Deployment"]},
    {"id":17,"title":"HTML & CSS Full Course – Beginner to Pro","platform":"freeCodeCamp","category":"Web Dev","level":"Beginner","rating":4.7,"price":0,"hours":12,"url":"https://www.youtube.com/watch?v=mU6anWqZJcc","skills":["HTML","CSS","Flexbox","Grid","Forms","Accessibility"]},
    {"id":18,"title":"Vue.js 3 – The Complete Guide","platform":"Udemy","category":"Web Dev","level":"Intermediate","rating":4.7,"price":13,"hours":32,"url":"https://www.udemy.com/course/vuejs-2-the-complete-guide/","skills":["Vue.js","Vuex","Vue Router","Composition API","TypeScript","Testing"]},
    {"id":19,"title":"Responsive Web Design Certification","platform":"freeCodeCamp","category":"Web Dev","level":"Beginner","rating":4.8,"price":0,"hours":20,"url":"https://www.freecodecamp.org/learn/2022/responsive-web-design/","skills":["HTML","CSS","Flexbox","Grid","Accessibility","Projects"]},
    {"id":20,"title":"TypeScript: The Complete Developer's Guide","platform":"Udemy","category":"Web Dev","level":"Intermediate","rating":4.6,"price":13,"hours":27,"url":"https://www.udemy.com/course/typescript-the-complete-developers-guide/","skills":["TypeScript","Generics","Decorators","Design Patterns","React","Node"]},
    {"id":21,"title":"Machine Learning Specialization (Andrew Ng)","platform":"Coursera","category":"AI / ML","level":"Intermediate","rating":4.9,"price":0,"hours":90,"url":"https://www.coursera.org/specializations/machine-learning-introduction","skills":["Supervised Learning","Neural Nets","Decision Trees","Python","TensorFlow"]},
    {"id":22,"title":"Deep Learning Specialization","platform":"Coursera","category":"AI / ML","level":"Advanced","rating":4.9,"price":0,"hours":120,"url":"https://www.coursera.org/specializations/deep-learning","skills":["CNNs","RNNs","Transformers","TensorFlow","Keras","NLP"]},
    {"id":23,"title":"Practical Deep Learning for Coders","platform":"fast.ai","category":"AI / ML","level":"Intermediate","rating":4.8,"price":0,"hours":35,"url":"https://course.fast.ai/","skills":["PyTorch","CNNs","NLP","Tabular Data","Diffusion Models","Deployment"]},
    {"id":24,"title":"AI For Everyone","platform":"Coursera","category":"AI / ML","level":"Beginner","rating":4.8,"price":0,"hours":10,"url":"https://www.coursera.org/learn/ai-for-everyone","skills":["AI Strategy","Use Cases","Ethics","ML Basics","AI Projects"]},
    {"id":25,"title":"Hugging Face NLP Course","platform":"Hugging Face","category":"AI / ML","level":"Intermediate","rating":4.8,"price":0,"hours":20,"url":"https://huggingface.co/learn/nlp-course/chapter1/1","skills":["Transformers","BERT","GPT","Fine-tuning","Tokenizers","Datasets"]},
    {"id":26,"title":"LangChain & LLM Apps – Short Course","platform":"DeepLearning.AI","category":"AI / ML","level":"Advanced","rating":4.7,"price":0,"hours":10,"url":"https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/","skills":["LangChain","LLMs","Chains","Agents","Vector DBs","RAG"]},
    {"id":27,"title":"Google Machine Learning Crash Course","platform":"Google","category":"AI / ML","level":"Beginner","rating":4.7,"price":0,"hours":15,"url":"https://developers.google.com/machine-learning/crash-course","skills":["ML Fundamentals","Linear Regression","Neural Nets","TensorFlow","Fairness"]},
    {"id":28,"title":"Reinforcement Learning Specialization","platform":"Coursera","category":"AI / ML","level":"Advanced","rating":4.7,"price":0,"hours":60,"url":"https://www.coursera.org/specializations/reinforcement-learning","skills":["Q-Learning","Policy Gradient","Actor-Critic","OpenAI Gym","Dynamic Programming"]},
    {"id":29,"title":"MLOps Specialization","platform":"Coursera","category":"AI / ML","level":"Advanced","rating":4.7,"price":0,"hours":50,"url":"https://www.coursera.org/specializations/machine-learning-engineering-for-production-mlops","skills":["MLOps","CI/CD","Model Monitoring","Feature Engineering","TFX","Kubeflow"]},
    {"id":30,"title":"Elements of AI","platform":"MinnaLearn","category":"AI / ML","level":"Beginner","rating":4.6,"price":0,"hours":12,"url":"https://www.elementsofai.com/","skills":["AI Basics","Search","Probability","ML Concepts","Ethics","Neural Nets"]},
    {"id":31,"title":"IBM Data Science Professional Certificate","platform":"Coursera","category":"Data Science","level":"Beginner","rating":4.6,"price":0,"hours":80,"url":"https://www.coursera.org/professional-certificates/ibm-data-science","skills":["Python","SQL","Data Viz","Machine Learning","Jupyter","Pandas"]},
    {"id":32,"title":"Data Analyst with Python Track","platform":"DataCamp","category":"Data Science","level":"Beginner","rating":4.7,"price":29,"hours":36,"url":"https://www.datacamp.com/tracks/data-analyst-with-python","skills":["Pandas","NumPy","Matplotlib","SQL","Statistics","Seaborn"]},
    {"id":33,"title":"Statistics with Python Specialization","platform":"Coursera","category":"Data Science","level":"Intermediate","rating":4.6,"price":0,"hours":45,"url":"https://www.coursera.org/specializations/statistics-with-python","skills":["Statistics","Probability","Regression","Bayesian","Inference","Python"]},
    {"id":34,"title":"Tableau for Beginners – Hands On","platform":"Udemy","category":"Data Science","level":"Beginner","rating":4.6,"price":13,"hours":11,"url":"https://www.udemy.com/course/tableau10/","skills":["Tableau","Data Viz","Dashboards","Calculated Fields","LOD Expressions"]},
    {"id":35,"title":"Kaggle Learn – Python, ML, SQL & more","platform":"Kaggle","category":"Data Science","level":"Beginner","rating":4.7,"price":0,"hours":15,"url":"https://www.kaggle.com/learn","skills":["Python","Pandas","ML","SQL","Data Viz","Feature Engineering"]},
    {"id":36,"title":"Data Science: R Basics – HarvardX","platform":"edX","category":"Data Science","level":"Beginner","rating":4.7,"price":0,"hours":16,"url":"https://www.edx.org/course/data-science-r-basics","skills":["R","Data Wrangling","Visualization","ggplot2","dplyr","tidyverse"]},
    {"id":37,"title":"Applied Data Science with Python","platform":"Coursera","category":"Data Science","level":"Intermediate","rating":4.6,"price":0,"hours":40,"url":"https://www.coursera.org/specializations/data-science-python","skills":["Python","Pandas","Matplotlib","Scikit-learn","NLTK","NetworkX"]},
    {"id":38,"title":"Power BI Full Course","platform":"freeCodeCamp","category":"Data Science","level":"Beginner","rating":4.6,"price":0,"hours":9,"url":"https://www.youtube.com/watch?v=NNSHu0rkew8","skills":["Power BI","DAX","Data Modeling","Dashboards","Power Query","Reports"]},
    {"id":39,"title":"AWS Cloud Practitioner Essentials","platform":"AWS Training","category":"Cloud","level":"Beginner","rating":4.7,"price":0,"hours":15,"url":"https://aws.amazon.com/training/digital/aws-cloud-practitioner-essentials/","skills":["AWS","Cloud Concepts","S3","EC2","IAM","Pricing","Security"]},
    {"id":40,"title":"Google Cloud Associate Cloud Engineer","platform":"Coursera","category":"Cloud","level":"Intermediate","rating":4.7,"price":0,"hours":60,"url":"https://www.coursera.org/professional-certificates/cloud-engineering-gcp","skills":["GCP","Kubernetes","Terraform","VPC","IAM","BigQuery"]},
    {"id":41,"title":"Azure Fundamentals AZ-900","platform":"Microsoft Learn","category":"Cloud","level":"Beginner","rating":4.8,"price":0,"hours":12,"url":"https://learn.microsoft.com/en-us/training/paths/azure-fundamentals/","skills":["Azure","Cloud Concepts","Compute","Networking","Storage","Security"]},
    {"id":42,"title":"Docker & Kubernetes: Practical Guide","platform":"Udemy","category":"Cloud","level":"Intermediate","rating":4.7,"price":15,"hours":24,"url":"https://www.udemy.com/course/docker-kubernetes-the-practical-guide/","skills":["Docker","Kubernetes","Containers","Microservices","CI/CD","Helm"]},
    {"id":43,"title":"Terraform on AWS – Full Course","platform":"freeCodeCamp","category":"Cloud","level":"Intermediate","rating":4.7,"price":0,"hours":13,"url":"https://www.youtube.com/watch?v=iRaai1IBlB0","skills":["Terraform","AWS","IaC","Modules","State Management","VPC"]},
    {"id":44,"title":"Linux Command Line Basics","platform":"Udacity","category":"Cloud","level":"Beginner","rating":4.6,"price":0,"hours":12,"url":"https://www.udacity.com/course/linux-command-line-basics--ud595","skills":["Linux","Bash","Shell Scripting","File System","Permissions","SSH"]},
    {"id":45,"title":"Site Reliability Engineering (SRE) Book","platform":"Google","category":"Cloud","level":"Advanced","rating":4.7,"price":0,"hours":10,"url":"https://sre.google/sre-book/table-of-contents/","skills":["SRE","Reliability","Monitoring","Alerting","On-Call","Error Budgets"]},
    {"id":46,"title":"Google UX Design Certificate","platform":"Coursera","category":"Design","level":"Beginner","rating":4.8,"price":0,"hours":80,"url":"https://www.coursera.org/professional-certificates/google-ux-design","skills":["UX","Figma","Wireframing","Prototyping","User Research","Usability Testing"]},
    {"id":47,"title":"UI / UX Design Bootcamp","platform":"Udemy","category":"Design","level":"Beginner","rating":4.6,"price":13,"hours":29,"url":"https://www.udemy.com/course/ui-ux-web-design-using-adobe-xd/","skills":["Adobe XD","Figma","UI Design","Color Theory","Typography","Prototyping"]},
    {"id":48,"title":"Graphic Design Specialization","platform":"Coursera","category":"Design","level":"Beginner","rating":4.6,"price":0,"hours":50,"url":"https://www.coursera.org/specializations/graphic-design","skills":["Photoshop","Illustrator","Typography","Layout","Branding","InDesign"]},
    {"id":49,"title":"Figma UI Design – Full Course","platform":"freeCodeCamp","category":"Design","level":"Beginner","rating":4.7,"price":0,"hours":6,"url":"https://www.youtube.com/watch?v=jwCmIBJ8Jtc","skills":["Figma","Components","Auto Layout","Prototyping","Design Systems"]},
    {"id":50,"title":"Canva Design School","platform":"Canva","category":"Design","level":"Beginner","rating":4.5,"price":0,"hours":5,"url":"https://www.canva.com/designschool/","skills":["Canva","Presentations","Social Media","Branding","Print Design"]},
    {"id":51,"title":"Google Cybersecurity Certificate","platform":"Coursera","category":"Cybersecurity","level":"Beginner","rating":4.8,"price":0,"hours":80,"url":"https://www.coursera.org/professional-certificates/google-cybersecurity","skills":["SIEM","Linux","Python","SQL","Network Security","Incident Response"]},
    {"id":52,"title":"CompTIA Security+ (SY0-701) Prep","platform":"Udemy","category":"Cybersecurity","level":"Intermediate","rating":4.7,"price":13,"hours":32,"url":"https://www.udemy.com/course/securityplus/","skills":["Network Security","Cryptography","Threats","Risk Management","Compliance"]},
    {"id":53,"title":"Ethical Hacking Bootcamp","platform":"Udemy","category":"Cybersecurity","level":"Intermediate","rating":4.6,"price":15,"hours":35,"url":"https://www.udemy.com/course/learn-ethical-hacking-from-scratch/","skills":["Kali Linux","Pen Testing","Metasploit","Network Hacking","Web App Hacking"]},
    {"id":54,"title":"Cybersecurity for Beginners","platform":"Udemy","category":"Cybersecurity","level":"Beginner","rating":4.5,"price":0,"hours":9,"url":"https://www.udemy.com/course/cybersecurity-for-absolute-beginners/","skills":["Security Basics","Threats","Passwords","Phishing","Privacy"]},
    {"id":55,"title":"TryHackMe – Pre-Security Path","platform":"TryHackMe","category":"Cybersecurity","level":"Beginner","rating":4.8,"price":0,"hours":40,"url":"https://tryhackme.com/path/outline/presecurity","skills":["Networking","Linux","Web Fundamentals","Cryptography","Windows","Bash"]},
    {"id":56,"title":"Hack The Box Academy – SOC Analyst Path","platform":"Hack The Box","category":"Cybersecurity","level":"Intermediate","rating":4.7,"price":0,"hours":60,"url":"https://academy.hackthebox.com/path/preview/soc-analyst","skills":["SIEM","Log Analysis","Phishing","DFIR","Network Traffic","Threat Intel"]},
    {"id":57,"title":"OWASP Top 10 – Web Security","platform":"OWASP","category":"Cybersecurity","level":"Intermediate","rating":4.7,"price":0,"hours":8,"url":"https://owasp.org/www-project-top-ten/","skills":["Web Security","XSS","SQL Injection","CSRF","IDOR","Broken Auth"]},
    {"id":58,"title":"Business Analytics Specialization","platform":"Coursera","category":"Business","level":"Intermediate","rating":4.6,"price":0,"hours":55,"url":"https://www.coursera.org/specializations/business-analytics","skills":["Excel","Regression","Visualization","Forecasting","Decision Making"]},
    {"id":59,"title":"Google Digital Marketing Certificate","platform":"Coursera","category":"Business","level":"Beginner","rating":4.7,"price":0,"hours":40,"url":"https://www.coursera.org/professional-certificates/google-digital-marketing-ecommerce","skills":["SEO","SEM","Email Marketing","Analytics","Social Media","E-commerce"]},
    {"id":60,"title":"Financial Markets – Yale University","platform":"Coursera","category":"Business","level":"Beginner","rating":4.8,"price":0,"hours":33,"url":"https://www.coursera.org/learn/financial-markets-global","skills":["Stocks","Bonds","Risk","Portfolio","Behavioral Finance","Options"]},
    {"id":61,"title":"Google Project Management Certificate","platform":"Coursera","category":"Business","level":"Intermediate","rating":4.7,"price":0,"hours":50,"url":"https://www.coursera.org/professional-certificates/google-project-management","skills":["Agile","Scrum","Waterfall","Risk Management","Stakeholders","Gantt Charts"]},
    {"id":62,"title":"Excel Skills for Business Specialization","platform":"Coursera","category":"Business","level":"Beginner","rating":4.9,"price":0,"hours":35,"url":"https://www.coursera.org/specializations/excel","skills":["Excel","Formulas","Pivot Tables","Charts","Macros","Data Analysis"]},
    {"id":63,"title":"Entrepreneurship – Wharton Specialization","platform":"Coursera","category":"Business","level":"Intermediate","rating":4.7,"price":0,"hours":45,"url":"https://www.coursera.org/specializations/wharton-entrepreneurship","skills":["Business Models","Funding","Launch","Growth","Finance","Leadership"]},
    {"id":64,"title":"Introduction to Public Speaking","platform":"Coursera","category":"Business","level":"Beginner","rating":4.8,"price":0,"hours":20,"url":"https://www.coursera.org/learn/public-speaking","skills":["Presentations","Storytelling","Delivery","Confidence","Structure","Persuasion"]},
]

ENROLLMENT_HISTORY = {
    "Programming":   [1200,1250,1300,1280,1350,1400,1380,1420,1500,1480,1550,1600,1620,1680,1700,1660,1750,1820,1800,1870,1950,1920,2000,2080,2100,2180,2200,2160,2280,2350,2320,2400,2500,2450,2550,2620],
    "AI / ML":       [800,850,900,950,1050,1100,1200,1300,1450,1500,1650,1800,1900,2100,2300,2500,2800,3100,3400,3700,4000,4300,4700,5100,5500,6000,6500,7000,7600,8200,8900,9600,10400,11200,12100,13000],
    "Web Dev":       [1500,1520,1540,1560,1580,1600,1620,1640,1660,1680,1700,1720,1740,1760,1780,1800,1820,1840,1860,1880,1900,1920,1940,1960,1980,2000,2020,2040,2060,2080,2100,2120,2140,2160,2180,2200],
    "Data Science":  [900,950,980,1020,1060,1100,1140,1180,1220,1260,1300,1350,1400,1450,1500,1550,1600,1650,1700,1750,1800,1860,1920,1980,2040,2100,2170,2240,2310,2380,2460,2540,2620,2700,2790,2880],
    "Cybersecurity": [400,420,440,470,500,530,560,600,640,680,720,770,820,880,940,1000,1070,1140,1220,1300,1390,1480,1580,1690,1800,1920,2050,2190,2340,2500,2670,2850,3050,3260,3480,3720],
    "Cloud":         [600,640,680,720,770,820,870,930,990,1060,1130,1210,1290,1380,1470,1570,1680,1790,1910,2040,2180,2330,2490,2660,2840,3030,3240,3460,3700,3950,4220,4510,4820,5150,5500,5880],
    "Design":        [500,510,520,530,540,550,565,580,595,610,625,640,655,670,685,700,715,730,745,760,775,795,815,835,855,875,900,925,950,975,1005,1035,1065,1095,1130,1165],
    "Business":      [700,720,740,760,785,810,835,860,890,920,950,985,1020,1055,1090,1130,1170,1210,1255,1300,1345,1395,1445,1500,1555,1610,1670,1730,1795,1860,1930,2000,2075,2150,2230,2315],
}
MONTHS = ["Jan 22","Feb 22","Mar 22","Apr 22","May 22","Jun 22","Jul 22","Aug 22","Sep 22","Oct 22","Nov 22","Dec 22","Jan 23","Feb 23","Mar 23","Apr 23","May 23","Jun 23","Jul 23","Aug 23","Sep 23","Oct 23","Nov 23","Dec 23","Jan 24","Feb 24","Mar 24","Apr 24","May 24","Jun 24","Jul 24","Aug 24","Sep 24","Oct 24","Nov 24","Dec 24"]
FORECAST_MONTHS = ["Jan 25","Feb 25","Mar 25","Apr 25","May 25","Jun 25"]

def poly_forecast(cat, n=6):
    """Simple polynomial regression degree-2 in pure Python."""
    y = ENROLLMENT_HISTORY[cat]
    N = len(y)
    # Build sums for normal equations with degree 2
    s = [0.0]*(2*2+1)
    for i in range(N):
        for k in range(2*2+1):
            s[k] += i**k
    rhs = [sum(y[i]*(i**j) for i in range(N)) for j in range(3)]
    # Solve 3x3 system
    A = [[s[j+k] for k in range(3)] for j in range(3)]
    b = rhs[:]
    for p in range(3):
        mx = max(range(p,3), key=lambda i: abs(A[i][p]))
        A[p],A[mx] = A[mx],A[p]; b[p],b[mx] = b[mx],b[p]
        for i in range(p+1,3):
            f = A[i][p]/A[p][p]
            for k in range(3): A[i][k] -= f*A[p][k]
            b[i] -= f*b[p]
    coef = [0.0]*3
    for i in range(2,-1,-1):
        coef[i] = (b[i] - sum(A[i][j]*coef[j] for j in range(i+1,3))) / A[i][i]
    pred = [max(0,int(coef[0]+coef[1]*(N+i)+coef[2]*(N+i)**2)) for i in range(n)]
    # R²
    mean_y = sum(y)/N
    ss_res = sum((y[i]-(coef[0]+coef[1]*i+coef[2]*i**2))**2 for i in range(N))
    ss_tot = sum((yi-mean_y)**2 for yi in y)
    r2 = round(1-ss_res/ss_tot, 4) if ss_tot else 1.0
    return pred, r2

def get_ml_context():
    """Build full ML stats string for Gemini."""
    cat_cnt = {}; cat_sum = {}; cat_n = {}
    for c in COURSES:
        k = c["category"]
        cat_cnt[k] = cat_cnt.get(k,0)+1
        cat_sum[k] = cat_sum.get(k,0)+c["rating"]
        cat_n[k] = cat_n.get(k,0)+1
    avg_r = {k: round(cat_sum[k]/cat_n[k],2) for k in cat_sum}
    lines = []
    for cat in ENROLLMENT_HISTORY:
        pred, r2 = poly_forecast(cat)
        last = ENROLLMENT_HISTORY[cat][-1]
        growth = round((pred[-1]-last)/last*100,1)
        lines.append(f"{cat}: current ~{last:,}/mo → forecast {pred[-1]:,}/mo (+{growth}%), R²={r2}, courses={cat_cnt.get(cat,0)}, avg_rating={avg_r.get(cat,'N/A')}")
    return "\n".join(lines)

# ── Routes ────────────────────────────────────────────────────────

@app.route("/")
def home():
    return send_from_directory(".", "frontend.html")

@app.route("/api/recommend", methods=["POST"])
def recommend():
    data = request.get_json(force=True) or {}
    msg = data.get("message","").strip()
    if not msg:
        return jsonify({"error":"No message"}), 400
    try:
        cat_list = [f"[{c['id']}] {c['title']} ({c['category']}, {c['level']}, {c['hours']}h, {'Free' if c['price']==0 else '$'+str(c['price'])})" for c in COURSES[:40]]
        prompt = f"""You are CourseCompass AI. Recommend 2-4 courses for the user.

Available courses:
{chr(10).join(cat_list)}

User: {msg}

Write a warm 2-3 sentence reply, then on a new line output ONLY:
COURSE_IDS:[id1,id2,id3]"""
        text = gemini_call(prompt)
        # (response via rate-limited call)
        m = re.search(r'COURSE_IDS:\s*\[([^\]]+)\]', text)
        ids = [int(x.strip()) for x in m.group(1).split(",") if x.strip().isdigit()] if m else []
        reply = re.sub(r'COURSE_IDS:\s*\[[^\]]*\]','',text).strip() or "Here are great courses for you!"
        courses = [c for c in COURSES if c["id"] in ids] or COURSES[:3]
        return jsonify({"reply": reply, "courses": courses})
    except Exception as ex:
        print(f"recommend error: {ex}")
        return jsonify({"reply":"Showing popular courses!","courses":COURSES[:3]})

@app.route("/api/ml/insights", methods=["GET"])
def ml_insights():
    cat_cnt={}; cat_sum={}; cat_n={}
    for c in COURSES:
        k=c["category"]
        cat_cnt[k]=cat_cnt.get(k,0)+1
        cat_sum[k]=cat_sum.get(k,0)+c["rating"]
        cat_n[k]=cat_n.get(k,0)+1
    avg_r={k:round(cat_sum[k]/cat_n[k],2) for k in cat_sum}
    # scatter
    scatter=[{"id":c["id"],"title":c["title"],"hours":c["hours"],"rating":c["rating"],"level":c["level"],"category":c["category"]} for c in COURSES]
    # top skills heatmap
    sf={}
    for c in COURSES:
        for s in c["skills"]: sf[s]=sf.get(s,0)+1
    top_skills=sorted(sf,key=lambda x:-sf[x])[:10]
    heatmap=[[sum(1 for c in COURSES if s1 in c["skills"] and s2 in c["skills"]) for s2 in top_skills] for s1 in top_skills]
    # forecasts
    forecasts={}; model_stats={}
    for cat in ENROLLMENT_HISTORY:
        pred,r2=poly_forecast(cat)
        forecasts[cat]=pred; model_stats[cat]={"r2":r2}
    # popularity
    pop=[]
    for cat,cnt in cat_cnt.items():
        avg_h=sum(c["hours"] for c in COURSES if c["category"]==cat)/cnt
        pop.append({"category":cat,"score":round(avg_r[cat]*cnt/(1+avg_h/50),2),"count":cnt,"avg_rating":avg_r[cat],"avg_hours":round(avg_h,1)})
    pop.sort(key=lambda x:-x["score"])
    return jsonify({
        "category_distribution":[{"category":k,"count":v} for k,v in cat_cnt.items()],
        "avg_ratings":[{"category":k,"rating":v} for k,v in avg_r.items()],
        "scatter":scatter,
        "heatmap":{"skills":top_skills,"matrix":heatmap},
        "trend":{"history":ENROLLMENT_HISTORY,"months":MONTHS,"forecast":forecasts,"forecast_months":FORECAST_MONTHS,"model_stats":model_stats},
        "popularity":pop,
        "total_courses":len(COURSES),
        "free_courses":sum(1 for c in COURSES if c["price"]==0),
    })

@app.route("/api/ml/chat", methods=["POST"])
def ml_chat():
    data = request.get_json(force=True) or {}
    msg = data.get("message","").strip()
    if not msg: return jsonify({"error":"No message"}), 400
    try:
        prompt = f"""You are an ML Insights analyst for CourseCompass.
You have access to course data and polynomial regression forecasts.

DATA:
{get_ml_context()}

User question: {msg}

Answer concisely and helpfully with specific numbers. Max 120 words."""
        reply_text = gemini_call(prompt)
        return jsonify({"reply": reply_text.strip()})
    except Exception as ex:
        print(f"ml_chat error: {ex}")
        return jsonify({"reply":"Sorry, couldn't analyze that. Try asking about trends, ratings, or growth!"})

@app.route("/api/ml/generate-graph", methods=["POST"])
def generate_graph():
    """AI generates graph config based on user request."""
    data = request.get_json(force=True) or {}
    request_text = data.get("request","").strip()
    if not request_text: return jsonify({"error":"No request"}), 400

    # Build dataset summary for Gemini
    cat_cnt={}; cat_sum={}; cat_n={}
    for c in COURSES:
        k=c["category"]
        cat_cnt[k]=cat_cnt.get(k,0)+1
        cat_sum[k]=cat_sum.get(k,0)+c["rating"]
        cat_n[k]=cat_n.get(k,0)+1
    avg_r={k:round(cat_sum[k]/cat_n[k],2) for k in cat_sum}
    forecasts={}
    for cat in ENROLLMENT_HISTORY:
        pred,r2=poly_forecast(cat)
        forecasts[cat]={"pred":pred,"r2":r2,"last":ENROLLMENT_HISTORY[cat][-1]}

    pop=[]
    for cat,cnt in cat_cnt.items():
        avg_h=sum(c["hours"] for c in COURSES if c["category"]==cat)/cnt
        pop.append({"cat":cat,"score":round(avg_r[cat]*cnt/(1+avg_h/50),2)})
    pop.sort(key=lambda x:-x["score"])

    prompt = f"""You are a data visualization expert for CourseCompass.
Available data:
- Category counts: {json.dumps(cat_cnt)}
- Avg ratings: {json.dumps(avg_r)}
- Popularity scores: {json.dumps({p['cat']:p['score'] for p in pop})}
- Forecast 6mo: {json.dumps({cat: forecasts[cat]['pred'] for cat in forecasts})}
- Enrollment history keys: {list(ENROLLMENT_HISTORY.keys())}
- Per-course: id, title, category, level, hours, rating, price (available as COURSES array)

User wants: {request_text}

Return ONLY valid JSON (no markdown) with this exact structure:
{{
  "title": "Chart title",
  "subtitle": "Short description",
  "type": "bar|line|doughnut|scatter|radar",
  "labels": [...],
  "datasets": [
    {{
      "label": "Dataset name",
      "data": [...],
      "backgroundColor": "color or array",
      "borderColor": "color or array",
      "fill": false
    }}
  ],
  "options_notes": "any special axis/scale notes"
}}

Use real numbers from the data above. Return ONLY JSON."""

    try:
        text = gemini_call(prompt).strip()
        # strip markdown fences
        text = re.sub(r'^```[a-z]*\n?','',text).rstrip('`').strip()
        cfg = json.loads(text)
        return jsonify({"success":True,"config":cfg})
    except Exception as ex:
        print(f"generate_graph error: {ex}")
        return jsonify({"success":False,"error":str(ex)})

@app.route("/api/status", methods=["GET"])
def status():
    return jsonify({"status":"running","courses":len(COURSES),"version":"4.0"})

if __name__ == "__main__":
    print("\n"+"="*55)
    print("🚀 CourseCompass  app.py  (Gemini 2.0 Flash)")
    print("="*55)
    print(f"  📚 {len(COURSES)} courses  |  🌐 http://localhost:5000")
    print(f"  POST /api/recommend      — AI course advisor")
    print(f"  GET  /api/ml/insights    — ML charts data")
    print(f"  POST /api/ml/chat        — ML analyst chat")
    print(f"  POST /api/ml/generate-graph  — AI graph builder")
    print("="*55+"\n")
    app.run(host="0.0.0.0", port=5000, debug=True) 