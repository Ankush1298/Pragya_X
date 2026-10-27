-- PragyaX Seed Data
-- Owned by: Nagin (Supabase Database Seeds)

-- 1. Seed Subjects
INSERT INTO subjects (id, slug, title, description, icon, is_active, question_count, difficulty)
VALUES
    ('subj_python', 'python', 'Python Programming', 'Master core Python semantics, data structures, and idiomatic problem-solving.', 'python', TRUE, 5, 'Beginner to Intermediate'),
    ('subj_webdev', 'webdev', 'Modern Full-Stack Web', 'React, TypeScript, state machines, and modern client-server architecture.', 'globe', FALSE, 5, 'Coming Soon'),
    ('subj_datasci', 'datasci', 'Data Science & ML', 'NumPy, Pandas, model evaluation metrics, and exploratory data analysis.', 'database', FALSE, 5, 'Coming Soon'),
    ('subj_cloud', 'cloud', 'Cloud & DevOps Architecture', 'Containerization, CI/CD pipelines, and scalable cloud services.', 'cloud', FALSE, 5, 'Coming Soon')
ON CONFLICT (id) DO NOTHING;

-- 2. Seed 5-Question Python Assessment (Deterministic & Conceptually Rich)
INSERT INTO assessment_questions (id, subject_id, question_number, question_text, option_a, option_b, option_c, option_d, correct_option, explanation, topic, difficulty)
VALUES
    (
        'q_py_1',
        'subj_python',
        1,
        'Consider the function definition:\ndef append_item(val, container=[]):\n    container.append(val)\n    return container\n\nWhat is returned after calling append_item(1) followed by append_item(2)?',
        'append_item(2) returns [2]',
        'append_item(2) returns [1, 2]',
        'A TypeError is raised because default arguments must be immutable',
        'append_item(2) returns [[1], [2]]',
        'B',
        'In Python, default parameter expressions are evaluated once when the function is defined, NOT each time it is invoked. Because lists are mutable, subsequent calls share the exact same default list instance unless overridden.',
        'Default Parameter Evaluation & Mutability',
        'Intermediate'
    ),
    (
        'q_py_2',
        'subj_python',
        2,
        'Given `data = [10, 20, 30, 40, 50]`, what does the slicing expression `data[1:4:-1]` produce?',
        '[40, 30, 20]',
        '[40, 30]',
        '[] (an empty list)',
        '[20, 30, 40]',
        'C',
        'The slice notation is [start:stop:step]. When step is -1, Python decrements from start down towards stop. Since start (1) is less than stop (4) and step is negative, the loop cannot proceed backwards, returning an empty list []. To slice in reverse from index 3 down to 1, one would write data[3:0:-1].',
        'Sequence Slicing & Negative Steps',
        'Intermediate'
    ),
    (
        'q_py_3',
        'subj_python',
        3,
        'Why does attempting `lookup = { [1, 2]: "coords" }` raise a `TypeError: unhashable type: ''list''`, whereas `lookup = { (1, 2): "coords" }` succeeds?',
        'Dictionaries can only store single primitive numbers or strings as keys',
        'Tuples have lower memory overhead than lists',
        'Dictionary keys must be hashable and immutable so their hash bucket remains invariant throughout execution',
        'Python syntax requires commas to be enclosed in parentheses',
        'C',
        'Python dictionaries use hash tables for O(1) key lookups. Keys must implement __hash__() and remain invariant. Since lists are mutable (their contents and identity can change), they are unhashable. Tuples containing only immutable elements are hashable.',
        'Hash Tables, Mutability & Dictionary Keys',
        'Beginner to Intermediate'
    ),
    (
        'q_py_4',
        'subj_python',
        4,
        'What is the fundamental operational difference between `nums_sq = [x*x for x in range(1_000_000)]` and `gen_sq = (x*x for x in range(1_000_000))`?',
        'The list comprehension executes faster in all memory scenarios',
        'The generator expression produces a generator object that evaluates items lazily on demand without allocating memory for 1,000,000 items upfront',
        'Generators can only produce integer values, whereas list comprehensions accept any data type',
        'There is no difference; parentheses in comprehensions are just alternative syntax',
        'B',
        'Square brackets `[...]` evaluate the list comprehension immediately and allocate memory for the entire million-element list in RAM. Parentheses `(...)` create a generator expression which uses lazy evaluation, computing values one by one on demand with O(1) memory overhead.',
        'List Comprehensions vs Generator Expressions',
        'Intermediate'
    ),
    (
        'q_py_5',
        'subj_python',
        5,
        'In Python variable scope resolution (the LEGB rule), which order of namespaces does the interpreter search when looking up an identifier?',
        'Local -> Enclosing -> Global -> Built-in',
        'Global -> Local -> Enclosing -> Built-in',
        'Built-in -> Global -> Enclosing -> Local',
        'Local -> Global -> Enclosing -> Built-in',
        'A',
        'Python resolves names using the LEGB rule: 1) Local (inside the current function), 2) Enclosing (in any enclosing nested functions/closures), 3) Global (at the module level), and 4) Built-in (standard Python builtins like print, len, range).',
        'LEGB Variable Scope & Closures',
        'Intermediate'
    )
ON CONFLICT (id) DO NOTHING;

-- 3. Seed Daily Challenge (Ankush''s Feature)
INSERT INTO daily_challenges (id, title, topic, difficulty, description, code_snippet, question_type, option_a, option_b, option_c, option_d, correct_option, explanation, points)
VALUES
    (
        'chal_today_py',
        'Python Daily Challenge: The List Mutation Trap',
        'Python List References & Shallow Copying',
        'Medium',
        'Determine the final output of the matrix operation where list multiplication creates shallow references instead of independent sublists.',
        'matrix = [[0] * 3] * 3\nmatrix[0][0] = 7\nprint([row[0] for row in matrix])',
        'multiple_choice',
        '[7, 0, 0]',
        '[7, 7, 7]',
        '[[7, 0, 0], [0, 0, 0], [0, 0, 0]]',
        'A TypeError occurs during inner assignment',
        'B',
        'When using `[[0] * 3] * 3`, the outer multiplication creates three references pointing to the exact same inner list in memory. Mutating `matrix[0][0] = 7` affects all three rows because they reference the identical object. To avoid this, use a comprehension: `[[0] * 3 for _ in range(3)]`.',
        50
    )
ON CONFLICT (id) DO NOTHING;
