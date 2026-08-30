from __future__ import annotations

from .schemas import ConceptNode, DomainAdapter, QuizQuestion, TopicBlueprint

# Dynamically synthesized concept nodes (one per free-text topic request),
# kept separate from the curated DSA graph but resolvable by every agent.
_DYNAMIC_NODES: dict[str, ConceptNode] = {}
_DYNAMIC_BRIEFS: dict[str, TopicBlueprint] = {}

# Hand-written warm-up quizzes for the curated DSA topics. Each distractor is
# deliberately tied to a known misconception so the diagnostic agent can flag it.
_CURATED_QUIZZES: dict[str, list[QuizQuestion]] = {
    "two-sum-hashmap": [
        QuizQuestion(
            question="You need to find two numbers in [2, 7, 11, 15] that add to 9. What's the most natural first idea?",
            options=[
                "Compare every number with every other number",
                "Sort the array first, then look at the ends",
                "Ask each number if it is bigger than the target",
                "Sum the whole array and divide by two",
            ],
            correct_index=0,
            misconception_tag="sorting is required first",
            explanation="The instinctive brute force is to try all pairs — a perfectly correct starting point.",
        ),
        QuizQuestion(
            question="A hash map makes Two Sum faster. Why?",
            options=[
                "It sorts the numbers automatically",
                "Checking whether a value is already in it takes about the same time no matter the size",
                "It stores the array in a smaller form",
                "It skips negative numbers",
            ],
            correct_index=1,
            misconception_tag="HashMap sorts data",
            explanation="Constant-time *average* membership lookup — no sorting involved.",
        ),
        QuizQuestion(
            question="While scanning [2, 7, 11, 15] for target 9, you're at value 2. What's the smart question to ask?",
            options=[
                "Is 2 the largest so far?",
                "Have I already seen 9 - 2 = 7?",
                "Is 2 next to a bigger number?",
                "Should I restart the scan from the beginning?",
            ],
            correct_index=1,
            misconception_tag="complement check not understood",
            explanation="The complement (target - current) is the whole trick of the optimized approach.",
        ),
    ],
    "contains-duplicate": [
        QuizQuestion(
            question="In [1, 2, 3, 1], how would you first check whether any value appears twice?",
            options=[
                "Compare each element only with its immediate neighbor",
                "Compare every element with every other element",
                "Count the total sum twice",
                "Remove the first and last elements",
            ],
            correct_index=1,
            misconception_tag="adjacent comparison is enough",
            explanation="Duplicates may not sit next to each other, so neighbor comparison alone fails.",
        ),
        QuizQuestion(
            question="What does a hash set give you in this problem?",
            options=[
                "A fast 'have I seen this before?' test",
                "An automatically sorted list",
                "A compressed copy of the array",
                "A way to sum elements faster",
            ],
            correct_index=0,
            misconception_tag="hash set purpose misunderstood",
            explanation="A set answers membership questions in constant average time.",
        ),
        QuizQuestion(
            question="Sorting the array first also detects duplicates. At what cost?",
            options=[
                "O(1) — sorting is free",
                "O(n log n) time for the sort itself",
                "O(n²) time for the sort",
                "Sorting cannot detect duplicates",
            ],
            correct_index=1,
            misconception_tag="sorting is free",
            explanation="Sorting costs O(n log n) — correct but slower than a hash set's O(n).",
        ),
    ],
    "valid-anagram": [
        QuizQuestion(
            question="Is 'listen' an anagram of 'silent'? What do you actually compare?",
            options=[
                "Whether both words have the same length only",
                "Whether each letter appears the same number of times in both",
                "Whether the first letters match",
                "Whether one word sorted equals the other reversed",
            ],
            correct_index=1,
            misconception_tag="length check equals anagram",
            explanation="Anagrams are about letter *counts*, not just length.",
        ),
        QuizQuestion(
            question="What data structure naturally counts letters?",
            options=[
                "A stack",
                "A frequency map (letter → count)",
                "A linked list",
                "A binary tree",
            ],
            correct_index=1,
            misconception_tag="frequency counting not known",
            explanation="A map keyed by character with counts as values is the standard tool.",
        ),
        QuizQuestion(
            question="Which approach is typically faster for anagrams?",
            options=[
                "Sorting both strings and comparing",
                "Counting letters in one pass with a map",
                "Reversing one string",
                "Comparing letter by letter without any structure",
            ],
            correct_index=1,
            misconception_tag="sorting is always fastest",
            explanation="O(n) counting beats O(n log n) sorting.",
        ),
    ],
    "best-time-stock": [
        QuizQuestion(
            question="Prices [7, 1, 5, 3, 6, 4]: what pair gives the best profit?",
            options=[
                "Buy 7, sell 6",
                "Buy 1, sell 6",
                "Buy 5, sell 6",
                "Buy 1, sell 3",
            ],
            correct_index=1,
            misconception_tag="misreading max difference",
            explanation="The max difference is 6 - 1 = 5.",
        ),
        QuizQuestion(
            question="Do you need to compare every buy/sell pair (brute force)?",
            options=[
                "Yes — there's no shortcut",
                "No — one pass tracking the minimum price so far is enough",
                "Yes, but only for sorted arrays",
                "No — sorting the prices first solves it",
            ],
            correct_index=1,
            misconception_tag="one pass not obvious",
            explanation="Track the min so far and the best profit — O(n), single pass.",
        ),
        QuizQuestion(
            question="Why can't you just sort prices and take last - first?",
            options=[
                "You can — that always works",
                "Because order in time matters: you must buy before you sell",
                "Because sorting loses the smallest value",
                "Because the last element is always the smallest",
            ],
            correct_index=1,
            misconception_tag="order invariance misunderstanding",
            explanation="Sorting destroys the time ordering that buy-before-sell requires.",
        ),
    ],
    "max-subarray": [
        QuizQuestion(
            question="In [-2, 1, -3, 4, -1, 2, 1, -5, 4], what does 'maximum subarray' mean?",
            options=[
                "The longest stretch of numbers",
                "The contiguous stretch with the largest sum",
                "The subsequence of positive numbers",
                "The pair with the highest product",
            ],
            correct_index=1,
            misconception_tag="subarray vs subsequence confusion",
            explanation="Contiguous stretch, largest possible sum.",
        ),
        QuizQuestion(
            question="A negative running sum while scanning — what's the smart move?",
            options=[
                "Keep carrying it; it might recover",
                "Drop it and restart the current sum from the next element",
                "Restart from the array's start",
                "Stop scanning entirely",
            ],
            correct_index=1,
            misconception_tag="Kadane restart logic not known",
            explanation="A negative prefix can only hurt what comes after — drop it (Kadane's insight).",
        ),
        QuizQuestion(
            question="Checking all subarrays brute force costs roughly…",
            options=[
                "O(n)",
                "O(n log n)",
                "O(n²)",
                "O(1)",
            ],
            correct_index=2,
            misconception_tag="quadratic cost not recognized",
            explanation="Every start × every end is O(n²); Kadane's does it in O(n).",
        ),
    ],
    "valid-parentheses": [
        QuizQuestion(
            question="For '([)]' — is this a valid bracket string?",
            options=[
                "Yes — every bracket is matched somewhere",
                "No — brackets must close in the reverse order they opened",
                "Yes — order doesn't matter, only counts",
                "It depends on the alphabet",
            ],
            correct_index=1,
            misconception_tag="nesting order ignored",
            explanation="Proper nesting requires last-opened, first-closed.",
        ),
        QuizQuestion(
            question="Which structure naturally tracks 'most recently opened' brackets?",
            options=[
                "A queue",
                "A stack",
                "A hash map",
                "A sorted array",
            ],
            correct_index=1,
            misconception_tag="stack not associated with nesting",
            explanation="LIFO order matches nesting order exactly.",
        ),
        QuizQuestion(
            question="After processing '()[]{}', what must be true about the stack?",
            options=[
                "It contains all the openers",
                "It's empty",
                "It contains one leftover closer",
                "It doesn't matter",
            ],
            correct_index=1,
            misconception_tag="residual stack overlooked",
            explanation="Leftover openers mean unclosed brackets — the stack must end empty.",
        ),
    ],
}


def get_diagnostic_quiz(concept_id: str | None) -> list[QuizQuestion]:
    """Curated quiz for known concepts; falls back to a dynamic topic's synthesized quiz."""
    if concept_id:
        quiz = _CURATED_QUIZZES.get(concept_id)
        if quiz:
            return list(quiz)
        brief = _DYNAMIC_BRIEFS.get(concept_id)
        if brief and brief.diagnostic_quiz:
            return list(brief.diagnostic_quiz)
    return []


def register_dynamic_concept(blueprint: TopicBlueprint) -> ConceptNode:
    """Convert a synthesized topic blueprint into a ConceptNode and register it."""
    node = ConceptNode(
        concept_id=blueprint.concept_id,
        title=blueprint.title,
        domain=blueprint.domain,
        subdomain=blueprint.subdomain,
        prerequisites=blueprint.prerequisites,
        canonical_definition=blueprint.canonical_definition,
        misconceptions=blueprint.misconceptions,
        explanation_depths=blueprint.explanation_depths or [blueprint.canonical_definition],
        representation_types=["array", "node", "edge", "highlight", "transition", "flow", "metric"],
        evaluation_modes=["prediction", "explanation", "debugging"],
    )
    _DYNAMIC_NODES[blueprint.concept_id] = node
    _DYNAMIC_BRIEFS[blueprint.concept_id] = blueprint
    return node


def get_topic_brief(concept_id: str) -> TopicBlueprint | None:
    return _DYNAMIC_BRIEFS.get(concept_id)


def get_concept_node(concept_id: str | None) -> ConceptNode:
    """Resolve a concept by id: curated DSA graph first, then dynamic registry."""
    adapter = get_cs_dsa_adapter()
    if concept_id:
        for node in adapter.concept_graph:
            if node.concept_id == concept_id:
                return node
        node = _DYNAMIC_NODES.get(concept_id)
        if node:
            return node
    return adapter.concept_graph[0]


def get_cs_dsa_adapter() -> DomainAdapter:
    # 1. Two Sum (Original)
    two_sum = ConceptNode(
        concept_id="two-sum-hashmap",
        title="Two Sum — HashMap lookup vs brute force",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "arrays",
            "loops",
            "basic hash map / dictionary semantics",
            "key-value lookup"
        ],
        canonical_definition=(
            "Two Sum is the problem of finding two numbers in an array that add up to a target. "
            "A brute-force approach checks every pair in O(n^2) time. A hash map approach stores "
            "seen values and checks whether the complement target - current_value has already appeared, "
            "reducing the average lookup cost to near O(1) per item and yielding overall O(n) average time."
        ),
        misconceptions=[
            "HashMap is magic",
            "HashMap sorts data",
            "A hash map is just a faster array without understanding lookup semantics",
            "The algorithm is faster because the array is smaller, not because lookup is constant average time"
        ],
        explanation_depths=[
            "simple intuition: checking the complement instead of scanning all pairs",
            "mechanism: store seen values and query for complement",
            "complexity: average O(n), worst-case O(n^2) under pathological collisions"
        ],
        representation_types=["comparison", "array", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 2. Contains Duplicate
    contains_duplicate = ConceptNode(
        concept_id="contains-duplicate",
        title="Contains Duplicate — Hash set vs sorting vs brute force",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "arrays",
            "loops",
            "hash sets"
        ],
        canonical_definition=(
            "Given an array of integers, determine if any value appears at least twice. "
            "A brute-force approach uses a nested loop in O(n²) time. Sorting allows adjacent "
            "element comparisons in O(n log n) time. A hash set tracks seen elements, inserting "
            "and looking up in average O(1) time per element, yielding an O(n) time and space solution."
        ),
        misconceptions=[
            "sorting is the only way to solve this",
            "a hash set lookup is always exactly O(1) with no exceptions",
            "you can find duplicates without sorting or a hash structure by comparing each element only to its immediate neighbor"
        ],
        explanation_depths=[
            "simple intuition: checking for set existence",
            "mechanism: insertion and set membership tests",
            "complexity: average O(n) time and space"
        ],
        representation_types=["array", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 3. Valid Anagram
    valid_anagram = ConceptNode(
        concept_id="valid-anagram",
        title="Valid Anagram — Frequency counting vs sorting",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "strings",
            "hash maps/frequency counting",
            "sorting"
        ],
        canonical_definition=(
            "Given two strings s and t, return true if t is an anagram of s. Anagrams use the "
            "exact same characters with the same frequencies. Methods include sorting both s and t "
            "and comparing characters (O(n log n) time, O(1) space), or frequency count mapping "
            "using a hash map or fixed-size array (O(n) time, O(n) or O(1) space)."
        ),
        misconceptions=[
            "two strings of different lengths can still be anagrams",
            "sorting is the only approach",
            "checking that both strings contain the same set of unique characters is sufficient"
        ],
        explanation_depths=[
            "simple intuition: character counting",
            "mechanism: update character counts and verify exact match",
            "complexity: O(n) time and O(1) space for fixed-size character sets"
        ],
        representation_types=["flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 4. Best Time to Buy and Sell Stock
    best_time_stock = ConceptNode(
        concept_id="best-time-stock",
        title="Best Time to Buy and Sell Stock — One pass vs brute force",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "arrays",
            "single-pass iteration",
            "tracking a running minimum"
        ],
        canonical_definition=(
            "Given daily prices, find the max profit from buying on one day and selling later. "
            "Brute force checks all buy/sell pairs in O(n²) time. A single-pass approach tracks "
            "the minimum price seen so far and computes best profit on-the-fly, running in O(n) "
            "time and using O(1) space."
        ),
        misconceptions=[
            "you must buy at the lowest price in the entire array regardless of when it occurs",
            "you can sell before you buy",
            "if no profitable transaction exists the answer should be negative"
        ],
        explanation_depths=[
            "simple intuition: one-pass profit tracking",
            "mechanism: update running min and compare potential profit",
            "complexity: O(n) time and O(1) space"
        ],
        representation_types=["array", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 5. Maximum Subarray (Kadane's Algorithm)
    max_subarray = ConceptNode(
        concept_id="max-subarray",
        title="Maximum Subarray — Kadane's algorithm vs brute force",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "arrays",
            "running sums",
            "greedy/dynamic-programming intuition"
        ],
        canonical_definition=(
            "Find the contiguous subarray with the largest sum. Brute force scans all subarrays "
            "in O(n²) or O(n³) time. Kadane's algorithm tracks a running sum that resets to the "
            "current element if the running sum becomes negative (contributing a net negative), "
            "running in O(n) time and using O(1) space."
        ),
        misconceptions=[
            "the running sum should reset to 0 whenever it goes negative",
            "the subarray must contain at least two elements",
            "if all numbers are negative the answer is 0"
        ],
        explanation_depths=[
            "simple intuition: greedy sub-problem choice",
            "mechanism: local maximum vs global maximum",
            "complexity: O(n) time and O(1) space"
        ],
        representation_types=["array", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 6. Valid Parentheses
    valid_parentheses = ConceptNode(
        concept_id="valid-parentheses",
        title="Valid Parentheses — Stack-based matching",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "strings",
            "stacks"
        ],
        canonical_definition=(
            "Determine if an input containing (), {}, [] is valid. Opening brackets must be "
            "closed by same type in correct order. Methods include stack-based LIFO matching "
            "(push open, pop/check close - O(n) time and space) or naive bracket count matching "
            "(which fails on ordering like ')(')."
        ),
        misconceptions=[
            "just counting the number of opening and closing brackets being equal is enough",
            "you can check validity with two pointers from each end",
            "an empty string is invalid"
        ],
        explanation_depths=[
            "simple intuition: last-in-first-out parsing",
            "mechanism: stack push/pop and mapping match",
            "complexity: O(n) time and space"
        ],
        representation_types=["stack", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 7. Reverse Linked List
    reverse_linked_list = ConceptNode(
        concept_id="reverse-linked-list",
        title="Reverse Linked List — Pointer redirection",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "linked lists",
            "pointers",
            "iteration"
        ],
        canonical_definition=(
            "Given the head of a singly linked list, reverse it and return the new head. "
            "An iterative approach tracks prev, current, and next pointers, updating current.next "
            "to point to prev in O(n) time and O(1) space. A recursive approach reverses the rest "
            "of the list and links the head to the end of the reversed tail in O(n) time and O(n) space."
        ),
        misconceptions=[
            "you can reverse a linked list the same way you reverse an array, by swapping values at mirrored positions",
            "you need extra memory proportional to the list to reverse it",
            "reversing means changing the values stored in each node"
        ],
        explanation_depths=[
            "simple intuition: reversing pointer arrows",
            "mechanism: pointer redirection with three pointers",
            "complexity: O(n) time, O(1) auxiliary space"
        ],
        representation_types=["comparison", "flow", "highlight", "transition", "node", "edge"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 8. Group Anagrams
    group_anagrams = ConceptNode(
        concept_id="group-anagrams",
        title="Group Anagrams — Hash map key categorization",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "strings",
            "hash maps",
            "sorting"
        ],
        canonical_definition=(
            "Given an array of strings, group the ones that are anagrams of each other. "
            "Sorting each string to generate a hash map key takes O(n * k log k) time. "
            "Alternatively, character frequency counting creates a tuple key of size 26 in O(n * k) "
            "time. Both map strings to keys and collect the list values."
        ),
        misconceptions=[
            "you need to compare every string to every other string",
            "anagram grouping requires the strings to be the same length as each other across the whole array",
            "sorting the whole array of strings groups anagrams together automatically"
        ],
        explanation_depths=[
            "simple intuition: grouping by standard signature key",
            "mechanism: key mapping and list accumulation",
            "complexity: O(n * k) time and space"
        ],
        representation_types=["array", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 9. Product of Array Except Self
    product_except_self = ConceptNode(
        concept_id="product-except-self",
        title="Product of Array Except Self — Prefix/Suffix products",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "arrays",
            "prefix/suffix products"
        ],
        canonical_definition=(
            "Given an array, return an array answer where answer[i] is the product of all elements except nums[i], "
            "without using division. Brute force recomputes products in O(n²) time. Prefix and suffix arrays take O(n) time and space. "
            "Optimizing allows single-pass accumulator tracking using the output array for prefix products and an on-the-fly "
            "suffix accumulator for O(1) auxiliary space."
        ),
        misconceptions=[
            "you should just divide the total product by each element",
            "a single pass without tracking both prefix and suffix products is enough",
            "the presence of a zero in the array means every output is zero"
        ],
        explanation_depths=[
            "simple intuition: prefix and suffix multiplication",
            "mechanism: accumulation scan from left and right",
            "complexity: O(n) time, O(1) auxiliary space"
        ],
        representation_types=["array", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 10. Top K Frequent Elements
    top_k_frequent = ConceptNode(
        concept_id="top-k-frequent",
        title="Top K Frequent Elements — Frequency heaps vs buckets",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "hash maps (frequency counting)",
            "heaps or bucket sort"
        ],
        canonical_definition=(
            "Given an integer array nums and k, return the k most frequent elements. "
            "First compute a frequency map in O(n) time. Then, sort by frequency (O(n log n)), "
            "use a min-heap of size k (O(n log k)), or use bucket sort with frequency as indices (O(n))."
        ),
        misconceptions=[
            "sorting the original array numerically finds the most frequent elements",
            "a hash map alone, without a heap or bucket sort, is enough to get the top k in less than O(n log n)",
            "ties should be broken by numeric value"
        ],
        explanation_depths=[
            "simple intuition: frequency counting and tracking top k",
            "mechanism: min-heap operations or bucket array partitioning",
            "complexity: O(n) time and space using bucket sort"
        ],
        representation_types=["array", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    # 11. Longest Consecutive Sequence
    longest_consecutive = ConceptNode(
        concept_id="longest-consecutive",
        title="Longest Consecutive Sequence — Hash set scans",
        domain="CS",
        subdomain="Software/DSA",
        prerequisites=[
            "hash sets",
            "sequence detection"
        ],
        canonical_definition=(
            "Given an unsorted array of integers, find the length of the longest consecutive sequence in O(n) time. "
            "Sorting first yields O(n log n) time. Inserting all numbers into a hash set allows checking for sequence starts "
            "(num - 1 not in set) and counting increments in O(1) average lookup, resulting in overall O(n) time."
        ),
        misconceptions=[
            "sorting is required to solve this in linear time",
            "you need to check every number as a potential sequence start",
            "the sequence must appear in order in the original array"
        ],
        explanation_depths=[
            "simple intuition: starting sequence tracking from minimums",
            "mechanism: hash set membership query and loop count scans",
            "complexity: O(n) average time and space"
        ],
        representation_types=["array", "flow", "highlight", "transition"],
        evaluation_modes=["prediction", "explanation", "debugging"]
    )

    concept_graph = [
        two_sum,
        contains_duplicate,
        valid_anagram,
        best_time_stock,
        max_subarray,
        valid_parentheses,
        reverse_linked_list,
        group_anagrams,
        product_except_self,
        top_k_frequent,
        longest_consecutive
    ]

    return DomainAdapter(
        domain_id="CS",
        subdomain_id="Software/DSA",
        concept_graph=concept_graph,
        misconceptions={node.concept_id: node.misconceptions for node in concept_graph},
        explanation_templates={node.concept_id: node.canonical_definition for node in concept_graph},
        visualization_templates={node.concept_id: ("stack" if node.concept_id == "valid-parentheses" else ("linked-list" if node.concept_id == "reverse-linked-list" else "comparison")) for node in concept_graph},
        practice_templates={node.concept_id: "prediction and reasoning" for node in concept_graph},
        evaluation_rules={
            "must_explain_lookup_semantics": True,
            "must_distinguish_bruteforce_vs_optimized": True
        }
    )
