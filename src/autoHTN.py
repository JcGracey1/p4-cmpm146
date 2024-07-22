import pyhop
import json

def check_enough(state, ID, item, num):
    if getattr(state, item)[ID] >= num:
        return []
    return False

def produce_enough(state, ID, item, num):
    return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods('have_enough', check_enough, produce_enough)

def produce(state, ID, item):
    return [('produce_{}'.format(item), ID)]

pyhop.declare_methods('produce', produce)

def make_method(name, rule):
    def method(state, ID):
        subtasks = []
        if 'Requires' in rule:
            for required_item, quantity in rule['Requires'].items():
                subtasks.append(('have_enough', ID, required_item, quantity))
        if 'Consumes' in rule:
            for consumed_item, quantity in rule['Consumes'].items():
                if getattr(state, consumed_item)[ID] < quantity:
                    return False
                subtasks.append(('have_enough', ID, consumed_item, quantity))
        subtasks.append(('op_{}'.format(name), ID))
        return subtasks
    return method

def declare_methods(data):
    for item in data['Items']:
        methods = []
        for name, recipe in data['Recipes'].items():
            if isinstance(recipe, dict) and 'Produces' in recipe and item in recipe['Produces']:
                method = make_method(name, recipe)
                methods.append(method)
        if methods:
            pyhop.declare_methods('produce_{}'.format(item), *methods)

def make_operator(rule):
    def operator(state, ID):
        if 'Requires' in rule:
            for item, quantity in rule['Requires'].items():
                if getattr(state, item)[ID] < quantity:
                    return False
        if 'Consumes' in rule:
            for item, quantity in rule['Consumes'].items():
                if getattr(state, item)[ID] < quantity:
                    return False
        if 'Produces' in rule:
            for item, quantity in rule['Produces'].items():
                setattr(state, item, getattr(state, item)[ID] + quantity)
        if 'Consumes' in rule:
            for item, quantity in rule['Consumes'].items():
                setattr(state, item, getattr(state, item)[ID] - quantity)
        if 'Time' in rule:
            state.time[ID] -= rule['Time']
        return state
    return operator

def declare_operators(data):
    operators = []
    for name, recipe in data['Recipes'].items():
        if isinstance(recipe, dict):
            op_name = 'op_' + name
            op = make_operator(recipe)
            globals()[op_name] = op  # to ensure the operator is accessible globally
            operators.append(op)
        else:
            print("Recipe is not a dictionary or missing 'Name':", name)
    pyhop.declare_operators(*operators)

def add_heuristic(data, ID):
    def heuristic(state, curr_task, tasks, plan, depth, calling_stack):
        return False

    pyhop.add_check(heuristic)

def set_up_state(data, ID, time=0):
    state = pyhop.State('state')
    state.time = {ID: time}

    for item in data['Items']:
        setattr(state, item, {ID: 0})

    for item in data['Tools']:
        setattr(state, item, {ID: 0})

    for item, num in data['Initial'].items():
        setattr(state, item, {ID: num})

    return state

def set_up_goals(data, ID):
    goals = []
    for item, num in data['Goal'].items():
        goals.append(('have_enough', ID, item, num))

    return goals

if __name__ == '__main__':
    rules_filename = 'crafting.json'

    with open(rules_filename) as f:
        data = json.load(f)

    state = set_up_state(data, 'agent', time=239)  # allot time here
    goals = set_up_goals(data, 'agent')

    declare_operators(data)  # new code
    declare_methods(data)    # new code
    add_heuristic(data, 'agent')

    # pyhop.print_operators()
    # pyhop.print_methods()

    # Hint: verbose output can take a long time even if the solution is correct; 
    # try verbose=1 if it is taking too long
    pyhop.pyhop(state, goals, verbose=3)
    # pyhop.pyhop(state, [('have_enough', 'agent', 'cart', 1),('have_enough', 'agent', 'rail', 20)], verbose=3)
