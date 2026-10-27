"""
Curated curriculum content for the four launch subjects (Python, Biology, Business, AI/ML).

One data shape for every subject so the learning engine stays subject-agnostic:
  module -> lesson (markdown) + practice questions (server-graded MCQ) ; subject -> 4 projects.
Answer keys live ONLY here (server side); public accessors strip them.
Content is hand-authored study material, not an accredited syllabus.
"""

from typing import Any, Dict, List, Optional

SUBJECT_TITLES = {
    "subj_python": "Python Programming",
    "subj_biology": "Foundational Biology",
    "subj_business": "Business & Entrepreneurship",
    "subj_aiml": "Artificial Intelligence & Machine Learning",
}


def _mod(sid: str, mid: str, title: str, desc: str, diff: str, mins: int, pre: List[str],
         kw: List[str], lesson: str, qs: List[tuple]) -> Dict[str, Any]:
    return {
        "catalog": {"id": mid, "title": title, "description": desc, "subject_id": sid, "difficulty": diff,
                    "estimated_minutes": mins, "prerequisite_module_ids": pre, "keywords": kw},
        "lesson": lesson,
        "questions": [
            {"id": f"{mid}_p{i + 1}", "question": q[0], "options": q[1], "answer": q[2], "explanation": q[3],
             "difficulty": ("Easy", "Medium", "Hard")[min(i, 2)]}
            for i, q in enumerate(qs)
        ],
    }


# ---------------------------------------------------------------- PYTHON (module ids match roadmap_service)
_PY = "subj_python"
PYTHON_CONTENT = [
    _mod(_PY, "mod_py_types", "Python Data Types, Variables & Memory", "Primitives, mutability and identity.",
         "Beginner", 25, [], ["type", "variable", "mutability", "memory", "default parameter"],
         "**Names, not boxes.** A Python variable is a name bound to an object. `int`, `str`, `tuple` are *immutable*; "
         "`list`, `dict`, `set` are *mutable* and can change in place.\n\n```python\na = [1]\nb = a\nb.append(2)\nprint(a)  # [1, 2] — same object\n```\n"
         "Use `is` for identity and `==` for equality. Never use a mutable default argument (`def f(x=[])`): it is created once and shared across calls.",
         [("What does `a = [1]; b = a; b.append(2); print(a)` print?", ["[1]", "[1, 2]", "[2]", "Error"], 1,
           "`b` and `a` name the same list, so the append is visible through both."),
          ("Which of these is immutable?", ["list", "dict", "tuple", "set"], 2, "Tuples cannot be changed after creation."),
          ("`def add(x, acc=[]): acc.append(x); return acc` — what does `add(1); add(2)` return the 2nd time?",
           ["[2]", "[1, 2]", "[1]", "Error"], 1, "The default list is created once at definition time and reused.")]),
    _mod(_PY, "mod_py_collections", "Lists, Tuples, Dictionaries & Slicing", "Sequences, hashing and slice syntax.",
         "Beginner", 30, ["mod_py_types"], ["list", "tuple", "dict", "set", "slice", "hash", "collection"],
         "**Slicing** is `seq[start:stop:step]` — `stop` is exclusive and negative indexes count from the end.\n\n```python\nx = [0,1,2,3,4,5]\nx[1:4]    # [1, 2, 3]\nx[::-1]   # reversed copy\n```\n"
         "**Dict keys must be hashable** (immutable): strings, numbers and tuples work; lists do not. Sets give O(1) membership tests.",
         [("What is `[0,1,2,3,4,5][1:4]`?", ["[1,2,3,4]", "[1,2,3]", "[0,1,2,3]", "[2,3,4]"], 1, "Stop index 4 is exclusive."),
          ("Which can be a dictionary key?", ["[1, 2]", "{1, 2}", "(1, 2)", "{'a': 1}"], 2, "Only hashable (immutable) values; a tuple of ints is hashable."),
          ("What does `[0,1,2,3,4,5][::-1]` return?", ["[5,4,3,2,1,0]", "[0]", "[5]", "Error"], 0, "A step of -1 walks the whole list backwards.")]),
    _mod(_PY, "mod_py_functions", "Functions, Scope (LEGB) & Closures", "Definitions, *args/**kwargs, scope rules.",
         "Intermediate", 35, ["mod_py_collections"], ["function", "scope", "legb", "closure", "args", "kwargs"],
         "Python resolves names in **L**ocal → **E**nclosing → **G**lobal → **B**uilt-in order. A *closure* is an inner function that remembers variables of its enclosing function.\n\n"
         "```python\ndef counter():\n    n = 0\n    def inc():\n        nonlocal n\n        n += 1\n        return n\n    return inc\n```\nWithout `nonlocal`, `n += 1` would raise `UnboundLocalError`.",
         [("What does LEGB stand for?", ["Local, Enclosing, Global, Built-in", "List, Env, Global, Base", "Local, External, Global, Built-in", "Loop, Enclosing, Global, Block"], 0, "That is the lookup order."),
          ("Which keyword lets an inner function rebind an enclosing variable?", ["global", "nonlocal", "static", "outer"], 1, "`nonlocal` targets the nearest enclosing function scope."),
          ("What does `*args` collect?", ["Keyword arguments", "Extra positional arguments as a tuple", "A dict", "Nothing"], 1, "Extra positional arguments arrive as a tuple.")]),
    _mod(_PY, "mod_py_comprehensions", "Comprehensions & Functional Idioms", "Comprehensions vs generators, map/filter.",
         "Intermediate", 30, ["mod_py_functions"], ["comprehension", "generator expression", "lambda", "map", "filter"],
         "`[x*x for x in range(5) if x % 2 == 0]` builds a list immediately. Replacing `[]` with `()` gives a **generator expression** that produces values lazily and uses constant memory.\n\n"
         "```python\nsquares = (x*x for x in range(10**9))  # no memory blow-up\nnext(squares)  # 0\n```\nGenerators are single-pass: once consumed they are empty.",
         [("What is the main difference between `[x for x in r]` and `(x for x in r)`?", ["Speed only", "The list is built eagerly, the generator lazily", "Generators are mutable", "No difference"], 1, "Lazy evaluation is the point."),
          ("`g = (i for i in range(3)); list(g); list(g)` — second `list(g)` gives?", ["[0,1,2]", "[]", "Error", "[0]"], 1, "A generator is exhausted after one pass."),
          ("Which builds a dict?", ["{k: v for k, v in pairs}", "[k: v for k, v in pairs]", "(k: v for ...)", "dict[k, v]"], 0, "Dict comprehensions use braces with key: value.")]),
    _mod(_PY, "mod_py_oop", "Object-Oriented Python", "Classes, inheritance and dunder methods.",
         "Intermediate", 35, ["mod_py_functions"], ["class", "oop", "inheritance", "object", "dunder"],
         "A class bundles data and behaviour. `__init__` initialises an instance; `self` is the instance. Subclasses reuse behaviour via inheritance and `super()`.\n\n"
         "```python\nclass Animal:\n    def __init__(self, name): self.name = name\n    def speak(self): return '...'\nclass Dog(Animal):\n    def speak(self): return 'Woof'\n```\nDunder methods like `__repr__` and `__eq__` customise built-in behaviour.",
         [("What is `self`?", ["A keyword for classes", "The instance the method is called on", "A global", "The parent class"], 1, "Python passes the instance as the first argument."),
          ("Which call runs the parent implementation?", ["parent()", "super()", "base.call()", "self.parent"], 1, "`super()` proxies to the next class in the MRO."),
          ("Which method controls `repr(obj)`?", ["__str__", "__repr__", "__init__", "__call__"], 1, "`__repr__` is the developer-facing representation.")]),
    _mod(_PY, "mod_py_generators", "Iterators & Generators", "Lazy sequences with yield.",
         "Advanced", 30, ["mod_py_comprehensions"], ["generator", "iterator", "yield"],
         "A function containing `yield` is a **generator function**: calling it returns an iterator that pauses at each `yield` and resumes on `next()`.\n\n"
         "```python\ndef countdown(n):\n    while n > 0:\n        yield n\n        n -= 1\n```\nIterators implement `__iter__` and `__next__`; `StopIteration` signals the end.",
         [("What does `yield` do?", ["Ends the program", "Pauses the function and produces a value", "Raises an error", "Returns a list"], 1, "State is kept between resumptions."),
          ("A generator function call returns:", ["A list", "A generator (iterator) object", "None", "A tuple"], 1, "Nothing runs until iteration starts."),
          ("What signals the end of iteration?", ["return None", "StopIteration", "break", "EOFError"], 1, "`for` loops catch StopIteration for you.")]),
    _mod(_PY, "mod_py_decorators", "Decorators", "Wrapping functions to add behaviour.",
         "Advanced", 30, ["mod_py_oop"], ["decorator", "wrapper", "functools"],
         "A decorator is a function that takes a function and returns a new one. `@deco` above `def f` is shorthand for `f = deco(f)`.\n\n"
         "```python\nimport functools\ndef timed(fn):\n    @functools.wraps(fn)\n    def wrapper(*a, **k):\n        return fn(*a, **k)\n    return wrapper\n```\n`functools.wraps` preserves the wrapped function's name and docstring.",
         [("`@deco def f(): ...` is equivalent to:", ["f = deco(f)", "deco = f(deco)", "f = deco", "deco(f())"], 0, "The decorator receives the function object."),
          ("Why use `functools.wraps`?", ["Speed", "Keep the original name and docstring", "Enable async", "Make it a class"], 1, "Without it the wrapper hides the metadata."),
          ("A decorator typically returns:", ["A string", "A callable", "A module", "Nothing"], 1, "Usually a wrapper function.")]),
    _mod(_PY, "mod_py_async", "Async Programming with asyncio", "Coroutines and the event loop.",
         "Advanced", 40, ["mod_py_generators", "mod_py_decorators"], ["async", "await", "asyncio", "coroutine"],
         "`async def` defines a coroutine; `await` suspends it until an awaitable finishes, letting the event loop run other tasks. Great for I/O-bound work, not CPU-bound work.\n\n"
         "```python\nimport asyncio\nasync def main():\n    await asyncio.sleep(1)\nasyncio.run(main())\n```\nUse `asyncio.gather(...)` to run several coroutines concurrently.",
         [("`await` can only be used inside:", ["Any function", "An `async def` function", "A class body", "A lambda"], 1, "It suspends a coroutine."),
          ("Asyncio mainly helps with:", ["CPU-bound loops", "I/O-bound concurrency", "GPU work", "Compilation"], 1, "While waiting on I/O the loop runs other tasks."),
          ("Which runs coroutines concurrently?", ["asyncio.gather", "asyncio.sleep", "time.sleep", "threading.join"], 0, "`gather` schedules them together.")]),
]

# ---------------------------------------------------------------- BIOLOGY
_BIO = "subj_biology"
BIOLOGY_CONTENT = [
    _mod(_BIO, "mod_bio_cells", "Cells & Organelles", "Structure and function inside the cell.", "Beginner", 25, [],
         ["cell", "organelle", "mitochondria", "membrane"],
         "All life is made of cells. **Prokaryotes** (bacteria) lack a nucleus; **eukaryotes** have a nucleus and organelles. "
         "The **mitochondrion** makes ATP through respiration, the **ribosome** builds proteins, the **nucleus** stores DNA, and the **chloroplast** (plants) runs photosynthesis.",
         [("Which organelle is the main site of ATP production?", ["Ribosome", "Mitochondrion", "Golgi body", "Lysosome"], 1, "Cellular respiration happens in mitochondria."),
          ("Which cells have no nucleus?", ["Prokaryotes", "Eukaryotes", "Plant cells", "Animal cells"], 0, "Prokaryotic DNA lies free in the cytoplasm."),
          ("Proteins are assembled by:", ["Ribosomes", "Vacuoles", "Chloroplasts", "Centrioles"], 0, "Ribosomes translate mRNA into protein.")]),
    _mod(_BIO, "mod_bio_genetics", "DNA & Molecular Genetics", "Structure of DNA, replication and expression.", "Beginner", 30, ["mod_bio_cells"],
         ["dna", "genetics", "molecular", "rna", "replication"],
         "DNA is a double helix of nucleotides; bases pair **A–T** and **G–C**. Replication is *semi-conservative*: each new molecule keeps one old strand. "
         "Expression follows **DNA → (transcription) → mRNA → (translation) → protein**. In RNA, uracil (U) replaces thymine.",
         [("Which base pairs with adenine in DNA?", ["Guanine", "Cytosine", "Thymine", "Uracil"], 2, "A pairs with T in DNA."),
          ("Translation produces:", ["mRNA", "Protein", "DNA", "ATP"], 1, "Ribosomes read mRNA codons to make a polypeptide."),
          ("Semi-conservative replication means each daughter DNA has:", ["Two new strands", "One old and one new strand", "Two old strands", "RNA strands"], 1, "That is what Meselson–Stahl showed.")]),
    _mod(_BIO, "mod_bio_photosynthesis", "Plant Biology & Photosynthesis", "How plants capture light energy.", "Beginner", 30, ["mod_bio_cells"],
         ["plant", "photosynthesis", "chloroplast", "chlorophyll"],
         "Photosynthesis: `6CO₂ + 6H₂O + light → C₆H₁₂O₆ + 6O₂`. The **light reactions** (thylakoid membranes) make ATP and NADPH and release O₂ from water; the **Calvin cycle** (stroma) uses them to fix CO₂ into sugar.",
         [("Where is O₂ released from in photosynthesis?", ["CO₂", "Water", "Glucose", "ATP"], 1, "Light reactions split water (photolysis)."),
          ("The Calvin cycle takes place in the:", ["Thylakoid membrane", "Stroma", "Nucleus", "Mitochondrion"], 1, "The stroma holds the Calvin-cycle enzymes."),
          ("Which pigment mainly absorbs light?", ["Chlorophyll", "Melanin", "Haemoglobin", "Keratin"], 0, "Chlorophyll absorbs red and blue light.")]),
    _mod(_BIO, "mod_bio_mendel", "Mendelian Genetics", "Dominance, segregation and Punnett squares.", "Beginner", 30, ["mod_bio_genetics"],
         ["mendel", "mendelian", "inheritance", "punnett", "allele"],
         "Mendel showed traits are inherited as discrete units (genes) with **alleles**. In a monohybrid cross of two heterozygotes (`Aa × Aa`) the offspring genotype ratio is **1 AA : 2 Aa : 1 aa** and the phenotype ratio is **3 dominant : 1 recessive**.",
         [("Aa × Aa gives what phenotype ratio (complete dominance)?", ["1:1", "3:1", "1:2:1", "9:3:3:1"], 1, "Three dominant-looking for every one recessive."),
          ("An individual with alleles Aa is:", ["Homozygous dominant", "Heterozygous", "Homozygous recessive", "Haploid"], 1, "Two different alleles = heterozygous."),
          ("Law of segregation says:", ["Alleles separate during gamete formation", "Genes never mix", "All traits blend", "Alleles are lost"], 0, "Each gamete gets one allele of each gene.")]),
    _mod(_BIO, "mod_bio_enzymes", "Biochemistry & Enzymes", "Catalysis, kinetics and inhibition.", "Beginner", 30, ["mod_bio_cells"],
         ["enzyme", "biochemistry", "kinetics", "catalyst", "substrate"],
         "Enzymes are biological catalysts that **lower activation energy** without being used up. Rate rises with substrate concentration until the enzyme saturates (V<sub>max</sub>). Extreme temperature or pH **denatures** the enzyme. "
         "A *competitive* inhibitor competes for the active site; raising substrate can overcome it.",
         [("Enzymes work by:", ["Raising activation energy", "Lowering activation energy", "Being consumed", "Adding heat"], 1, "They speed reactions by lowering the energy barrier."),
          ("Very high temperature typically causes:", ["Higher rate forever", "Denaturation", "More substrate", "New enzymes"], 1, "The 3D shape unfolds and activity is lost."),
          ("Competitive inhibition is reduced by:", ["Adding more substrate", "Lowering pH", "Removing enzyme", "Cooling"], 0, "More substrate outcompetes the inhibitor.")]),
]

# ---------------------------------------------------------------- BUSINESS
_BUS = "subj_business"
BUSINESS_CONTENT = [
    _mod(_BUS, "mod_biz_accounting", "Financial Accounting Basics", "Income statement, balance sheet, cash flow.", "Beginner", 30, [],
         ["accounting", "financial", "statement", "balance sheet", "profit"],
         "Three core statements: the **income statement** (revenue − expenses = profit), the **balance sheet** (`Assets = Liabilities + Equity`), and the **cash-flow statement** (cash in/out). Profit is not cash: a sale on credit raises revenue before cash arrives.",
         [("The accounting equation is:", ["Assets = Liabilities + Equity", "Assets = Revenue − Costs", "Equity = Assets + Liabilities", "Profit = Assets"], 0, "The balance sheet always balances."),
          ("Revenue 100, expenses 70. Profit is:", ["170", "30", "70", "100"], 1, "100 − 70."),
          ("Why can a profitable firm run out of cash?", ["It cannot", "Customers may pay late", "Profit equals cash", "Taxes vanish"], 1, "Timing differences between profit and cash.")]),
    _mod(_BUS, "mod_biz_economics", "Supply, Demand & Pricing", "Markets, elasticity and price setting.", "Beginner", 30, ["mod_biz_accounting"],
         ["supply", "demand", "microeconomics", "price", "elasticity"],
         "When price rises, quantity demanded falls and quantity supplied rises; the market clears at the **equilibrium price**. **Elastic** demand means customers are price-sensitive (raising price cuts revenue); **inelastic** demand means they are not.",
         [("If demand rises and supply is unchanged, price tends to:", ["Fall", "Rise", "Stay fixed", "Hit zero"], 1, "More buyers chasing the same supply."),
          ("Elastic demand means:", ["Quantity barely reacts to price", "Quantity reacts strongly to price", "Price is fixed", "Supply is fixed"], 1, "Customers are price-sensitive."),
          ("A price ceiling below equilibrium causes:", ["Surplus", "Shortage", "Balance", "No change"], 1, "Demand exceeds supply at the capped price.")]),
    _mod(_BUS, "mod_biz_marketing", "Marketing Strategy & the 4 Ps", "Product, price, place, promotion.", "Beginner", 25, ["mod_biz_economics"],
         ["marketing", "4 ps", "segmentation", "positioning"],
         "The **4 Ps**: Product, Price, Place, Promotion. Strategy starts with **segmentation** (who), **targeting** (which segment first) and **positioning** (why you). A narrow beachhead segment beats a vague 'everyone'.",
         [("Which is NOT one of the 4 Ps?", ["Product", "Place", "People-count", "Promotion"], 2, "The Ps are product, price, place, promotion."),
          ("Positioning answers:", ["Where is the office", "Why should this segment pick us", "How much cash we have", "Who our investors are"], 1, "It states your distinct value."),
          ("A startup's best first target is usually:", ["Everyone", "A narrow, reachable segment", "A competitor's staff", "No one"], 1, "Focus lets you win a niche first.")]),
    _mod(_BUS, "mod_biz_unit", "Unit Economics & Startup Metrics", "CAC, LTV, margins and runway.", "Intermediate", 35, ["mod_biz_accounting", "mod_biz_marketing"],
         ["unit economics", "cac", "ltv", "startup", "metrics", "margin"],
         "**CAC** = marketing+sales cost ÷ new customers. **LTV** = average margin per period × expected lifetime. Healthy businesses usually target **LTV/CAC ≥ 3** and a CAC payback under ~12 months. **Runway** = cash ÷ monthly burn.",
         [("Spend ₹50,000 to win 100 customers. CAC is:", ["₹500", "₹5,000", "₹50", "₹100"], 0, "50,000 ÷ 100."),
          ("Cash ₹12 lakh, burn ₹2 lakh/month. Runway:", ["2 months", "6 months", "12 months", "24 months"], 1, "12 ÷ 2."),
          ("LTV is 2× CAC. This is generally:", ["Excellent", "Thin — improve margin or retention", "Impossible", "Irrelevant"], 1, "Rule of thumb target is 3× or more.")]),
    _mod(_BUS, "mod_biz_strategy", "Strategy & Competitive Moats", "Differentiation, switching costs and network effects.", "Intermediate", 30, ["mod_biz_unit"],
         ["strategy", "moat", "competitive", "network effect", "switching"],
         "A **moat** is a durable advantage: cost leadership, brand, **switching costs**, **network effects** (value grows with users) or regulation/IP. Porter's Five Forces: rivalry, new entrants, substitutes, supplier power, buyer power.",
         [("A network effect means:", ["More users make the product more valuable", "Costs fall with ads", "Fewer users is better", "Prices are fixed"], 0, "Value scales with the network."),
          ("High switching costs help a firm by:", ["Retaining customers", "Raising CAC", "Lowering margin", "Increasing rivalry"], 0, "Customers find leaving expensive."),
          ("Which is a Porter force?", ["Threat of substitutes", "Office size", "Founder age", "Logo colour"], 0, "Substitutes cap what you can charge.")]),
]

# ---------------------------------------------------------------- AI / ML
_ML = "subj_aiml"
AIML_CONTENT = [
    _mod(_ML, "mod_ml_paradigms", "Machine Learning Paradigms", "Supervised, unsupervised, reinforcement.", "Beginner", 25, [],
         ["paradigm", "supervised", "unsupervised", "reinforcement", "machine learning"],
         "**Supervised** learning maps inputs to known labels (classification, regression). **Unsupervised** learning finds structure without labels (clustering, dimensionality reduction). **Reinforcement** learning learns actions from rewards.",
         [("Predicting house price from features is:", ["Clustering", "Supervised regression", "Reinforcement", "Unsupervised"], 1, "Labelled continuous target."),
          ("Grouping customers without labels is:", ["Classification", "Clustering", "Regression", "Labelling"], 1, "Unsupervised clustering."),
          ("An agent learning from rewards is:", ["Supervised", "Reinforcement learning", "Clustering", "PCA"], 1, "Reward-driven.")]),
    _mod(_ML, "mod_ml_generalization", "Generalization & Overfitting", "Train/validation/test and bias–variance.", "Beginner", 30, ["mod_ml_paradigms"],
         ["generalization", "overfitting", "underfitting", "validation", "bias", "variance"],
         "A model **overfits** when it memorises training data: training error is low but validation error is high. **Underfitting** is high error on both. Fight overfitting with more data, regularisation, simpler models and early stopping. Never tune on the **test set**.",
         [("Low train error, high validation error indicates:", ["Underfitting", "Overfitting", "Perfect fit", "Data leakage fixed"], 1, "The model memorised training data."),
          ("Which helps reduce overfitting?", ["Regularisation", "Training longer on same data forever", "Using test data to tune", "Removing validation set"], 0, "Regularisation constrains the model."),
          ("The test set should be used to:", ["Tune hyper-parameters", "Give a final unbiased estimate", "Train", "Augment data"], 1, "Touch it once at the end.")]),
    _mod(_ML, "mod_ml_metrics", "Evaluation Metrics", "Precision, recall, F1 and accuracy traps.", "Intermediate", 30, ["mod_ml_generalization"],
         ["metric", "precision", "recall", "f1", "accuracy", "evaluation"],
         "**Precision** = TP/(TP+FP): of predicted positives, how many are right. **Recall** = TP/(TP+FN): of real positives, how many were found. **F1** is their harmonic mean. On imbalanced data accuracy misleads: predicting 'no fraud' for everything can be 99% accurate and useless.",
         [("TP=8, FP=2, FN=8. Precision?", ["0.8", "0.5", "0.2", "1.0"], 0, "8/(8+2)."),
          ("Same counts: recall?", ["0.8", "0.5", "0.2", "1.0"], 1, "8/(8+8)."),
          ("For rare-disease screening you most want high:", ["Recall", "Accuracy only", "Precision only", "Speed"], 0, "Missing a real case (FN) is costly.")]),
    _mod(_ML, "mod_ml_optimization", "Optimization & Gradient Descent", "Loss, gradients and learning rate.", "Intermediate", 30, ["mod_ml_generalization"],
         ["gradient", "optimization", "loss", "learning rate", "descent"],
         "Training minimises a **loss** by repeatedly stepping against the gradient: `w ← w − η·∇L(w)`. A learning rate η that is too large diverges; too small is slow. **SGD** uses mini-batches for noisy but cheap updates.",
         [("Gradient descent updates weights:", ["Along the gradient", "Against the gradient", "Randomly", "Never"], 1, "It moves downhill on the loss."),
          ("Loss exploding to infinity usually means:", ["Learning rate too large", "Learning rate too small", "Perfect training", "Too much data"], 0, "Steps overshoot the minimum."),
          ("Mini-batch SGD uses:", ["The whole dataset per step", "A small random subset per step", "One weight", "No data"], 1, "Cheaper, noisier updates.")]),
    _mod(_ML, "mod_ml_deep", "Neural Networks & Activations", "Layers, non-linearity and depth.", "Intermediate", 35, ["mod_ml_optimization", "mod_ml_metrics"],
         ["neural", "deep learning", "activation", "relu", "network", "backpropagation"],
         "A neural network stacks layers of weighted sums followed by a **non-linear activation** (ReLU, sigmoid, tanh). Without non-linearity, many layers collapse into one linear map. **Backpropagation** computes gradients layer by layer using the chain rule.",
         [("Why are activation functions needed?", ["Add non-linearity", "Reduce memory", "Normalise labels", "Speed I/O"], 0, "Otherwise the network is just linear."),
          ("ReLU(x) equals:", ["max(0, x)", "1/(1+e^-x)", "tanh(x)", "x²"], 0, "Zero for negatives, identity otherwise."),
          ("Backpropagation uses:", ["The chain rule", "Random search", "Clustering", "Sorting"], 0, "Gradients flow backwards layer by layer.")]),
]

CONTENT: Dict[str, List[Dict[str, Any]]] = {
    _PY: PYTHON_CONTENT, _BIO: BIOLOGY_CONTENT, _BUS: BUSINESS_CONTENT, _ML: AIML_CONTENT,
}
_MODULES: Dict[str, Dict[str, Any]] = {m["catalog"]["id"]: m for mods in CONTENT.values() for m in mods}

# ---------------------------------------------------------------- PROJECTS (4 levels per subject)


def _proj(sid: str, level: str, title: str, objective: str, skills: List[str], milestones: List[str],
          deliverables: str, rubric: List[str]) -> Dict[str, Any]:
    return {"id": f"proj_{sid.replace('subj_', '')}_{level.lower()}", "subject_id": sid, "level": level, "title": title,
            "objective": objective, "skills": skills, "milestones": milestones, "deliverables": deliverables,
            "rubric": rubric}


_LEVELS = ("Basic", "Intermediate", "Advanced", "Extreme")
PROJECTS: List[Dict[str, Any]] = [
    _proj(_PY, "Basic", "CLI Expense Tracker", "Build a command-line tool that records and totals expenses.",
          ["lists/dicts", "functions", "file I/O"], ["Design the data shape", "Add/list/total commands", "Persist to a JSON file"],
          "Source file + short README with usage examples.", ["Correct totals", "Handles bad input", "Readable functions"]),
    _proj(_PY, "Intermediate", "Text Analytics Toolkit", "Analyse a text file: word frequency, longest words, reading time.",
          ["comprehensions", "dicts", "modules"], ["Tokenise text", "Frequency + top-N report", "Unit tests for helpers"],
          "Package with tests and sample output.", ["Tests pass", "Idiomatic comprehensions", "Edge cases covered"]),
    _proj(_PY, "Advanced", "REST API with Caching Decorator", "Expose a small API and add a custom caching/timing decorator.",
          ["decorators", "OOP", "HTTP"], ["Define resources", "Write decorator with functools.wraps", "Document endpoints"],
          "Repository link + API docs.", ["Decorator is reusable", "Clear error handling", "Documented endpoints"]),
    _proj(_PY, "Extreme", "Concurrent Web Crawler", "Crawl pages concurrently with asyncio, respecting rate limits and robots.txt.",
          ["asyncio", "error handling", "design"], ["Single-page fetch", "Concurrent queue with limits", "Retry/back-off + metrics"],
          "Repository, design note, benchmark vs sequential.", ["Measured speed-up", "Graceful failures", "Respects politeness limits"]),
    _proj(_BIO, "Basic", "Cell Model Explainer", "Create an annotated diagram explaining organelle functions.",
          ["cell structure"], ["List organelles", "Draw and label", "Explain each in one line"],
          "Labelled diagram + one-page note.", ["Accurate labels", "Clear functions", "Own words"]),
    _proj(_BIO, "Intermediate", "Monohybrid Cross Study", "Predict and test inheritance ratios with Punnett squares for three traits.",
          ["Mendelian genetics"], ["Pick traits", "Draw crosses", "Compare expected vs simulated ratios"],
          "Worked crosses + a 50-trial coin-flip simulation table.", ["Correct genotype ratios", "Honest comparison", "Clear reasoning"]),
    _proj(_BIO, "Advanced", "Enzyme Activity Experiment Design", "Design a controlled experiment on temperature or pH effects on enzyme rate.",
          ["experiment design", "enzymes"], ["State hypothesis", "Identify variables/controls", "Plan data table and graph"],
          "Protocol + mock data analysis.", ["Valid controls", "Measurable outcome", "Sound conclusion"]),
    _proj(_BIO, "Extreme", "Photosynthesis Case Analysis", "Analyse a published dataset on light intensity vs photosynthetic rate and critique the study.",
          ["data interpretation", "scientific reasoning"], ["Summarise methods", "Plot and interpret", "Critique limitations"],
          "Short report citing the dataset.", ["Correct interpretation", "Identifies limitations", "Evidence-based claims"]),
    _proj(_BUS, "Basic", "Lemonade Stand P&L", "Build a one-month profit and loss for a micro business.",
          ["accounting basics"], ["List revenue and costs", "Compute profit", "Explain the result"],
          "Spreadsheet + 5-line summary.", ["Correct arithmetic", "Realistic assumptions", "Clear summary"]),
    _proj(_BUS, "Intermediate", "Pricing Experiment Plan", "Choose a price for a product using demand evidence.",
          ["pricing", "elasticity"], ["Define product & segment", "Gather 3 competitor prices", "Recommend a price with reasoning"],
          "One-page recommendation.", ["Evidence-based", "Considers elasticity", "Clear recommendation"]),
    _proj(_BUS, "Advanced", "Unit Economics Model", "Model CAC, LTV, payback and runway for a startup idea.",
          ["unit economics"], ["Collect assumptions", "Build the model", "Run sensitivity cases"],
          "Spreadsheet model + memo.", ["Transparent assumptions", "Correct formulas", "Sensible sensitivity"]),
    _proj(_BUS, "Extreme", "Startup Pitch & Moat Analysis", "Write a 10-slide pitch with market sizing and competitive-moat argument.",
          ["strategy", "storytelling"], ["Problem & market", "Moat & model", "Defend against objections"],
          "Slide deck + Q&A notes.", ["Credible market sizing", "Moat is defensible", "Coherent story"]),
    _proj(_ML, "Basic", "Iris Classifier", "Train a simple classifier and report accuracy on a held-out split.",
          ["supervised learning", "train/test split"], ["Load data", "Train/test split", "Report accuracy"],
          "Notebook or script + results.", ["Proper split", "Reproducible", "Correct reporting"]),
    _proj(_ML, "Intermediate", "Imbalanced Data Evaluation", "Compare accuracy, precision, recall and F1 on an imbalanced dataset.",
          ["metrics", "overfitting"], ["Build baseline", "Compute full metric table", "Explain the trade-off"],
          "Notebook with metric table and commentary.", ["Correct metrics", "Shows accuracy trap", "Sound recommendation"]),
    _proj(_ML, "Advanced", "Gradient Descent From Scratch", "Implement linear regression with gradient descent and tune the learning rate.",
          ["optimization", "numpy"], ["Implement loss and gradient", "Plot convergence", "Compare learning rates"],
          "Code + convergence plots.", ["Correct gradients", "Convergence shown", "Learning-rate analysis"]),
    _proj(_ML, "Extreme", "End-to-End ML Experiment", "Frame a real problem, run controlled experiments, and write a model card.",
          ["experiment design", "evaluation", "ethics"], ["Frame problem & metric", "Run ablations", "Write model card with limits"],
          "Repository + model card.", ["Rigorous validation", "Honest limitations", "Reproducible"]),
]
_PROJECTS: Dict[str, Dict[str, Any]] = {p["id"]: p for p in PROJECTS}

PASS_RATIO = 2 / 3  # practice score needed to complete a module


def is_curated(subject_id: Optional[str]) -> bool:
    return subject_id in CONTENT


def subject_modules(subject_id: str) -> List[Dict[str, Any]]:
    return CONTENT.get(subject_id, [])


def get_module(module_id: str) -> Optional[Dict[str, Any]]:
    return _MODULES.get(module_id)


def public_question(q: Dict[str, Any]) -> Dict[str, Any]:
    """Strip the answer key and explanation (revealed only after grading)."""
    return {"id": q["id"], "question": q["question"], "options": q["options"], "difficulty": q["difficulty"]}


def get_project(project_id: str) -> Optional[Dict[str, Any]]:
    return _PROJECTS.get(project_id)


def catalogs_for_roadmap() -> Dict[str, Dict[str, Dict[str, Any]]]:
    """Catalog dicts in the shape roadmap_service expects (key -> module template)."""
    out: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for sid, mods in CONTENT.items():
        out[sid] = {m["catalog"]["id"].split("_", 2)[-1]: dict(m["catalog"]) for m in mods}
    return out
