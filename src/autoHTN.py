import pyhop
import json

def check_enough(state, ID, item, num):
	if getattr(state, item)[ID] >= num: return []
	return False

def produce_enough(state, ID, item, num):
	return [('produce', ID, item), ('have_enough', ID, item, num)]

pyhop.declare_methods('have_enough', check_enough, produce_enough)

def produce(state, ID, item):
	return [('produce_{}'.format(item), ID)]

pyhop.declare_methods('produce', produce)

def extract_product_name(recipe):
	# return product
	name, details = recipe
	product = details['Produces']
	return next(iter(product))

def collect_requirements(details):
	requirements = dict()
	if 'Requires' in details:
		requirements.update(details['Requires'])
	if 'Consumes' in details:
		requirements.update(details['Consumes'])
	return requirements

def create_precondition(details, ID):
	preconditions = []
	requirements = collect_requirements(details)
	for item in requirements:
		preconditions.append(('have_enough', ID, item, requirements[item]))
	return preconditions

def construct_method(name, recipe):
	name, details = recipe
	func_name = name.replace(' ', "_")
	def method(state, ID):
		preconditions = create_precondition(details, ID)
		operator = "op_" + func_name
		preconditions.append((operator, ID))
		return preconditions

	method.__name__ = func_name
	return (details['Time'], method)

def declare_methods(data):
	names = data['Items'] + data['Tools']
	for name in names:
		tasks = []
		for recipe in data['Recipes'].items():
			current = extract_product_name(recipe)
			if name == current:
				task = construct_method(name, recipe)
				tasks.append(task)
		tasks.sort(key=lambda a: a[0], reverse=True)
		args = [b for a, b in tasks]
		pyhop.declare_methods("produce_" + name, *args)

def validate_items(details, category, state, ID):
	if category in details:
		requirements = details[category]
		for item in requirements:
			if getattr(state, item)[ID] < requirements[item]:
				return False
	return True

def update_game_state(details, state, ID):
	products = details['Produces']
	for i in products:
		value = getattr(state, i)[ID] + products[i]
		setattr(state, i, {ID: value})
	if 'Consumes' in details:
		requirements = details['Consumes']
		for i in requirements:
			value = getattr(state, i)[ID] - requirements[i]
			setattr(state, i, {ID: value})

	time_key = 'Time'
	time_value = getattr(state, 'time')[ID] - details[time_key]
	setattr(state, 'time', {ID: time_value})

def verify_time(details, state, ID):
	time_value = getattr(state, 'time')[ID]
	return time_value >= details['Time']

def construct_operator(recipe):
	name, details = recipe
	def operator(state, ID):
		if verify_time(details, state, ID) and validate_items(details, 'Requires', state, ID) and validate_items(details, 'Consumes', state, ID):
			update_game_state(details, state, ID)
			return state
		return False

	func_name = "op_" + name.replace(' ', "_")
	operator.__name__ = func_name
	return operator

def declare_operators(data):
	for recipe in data['Recipes'].items():
		pyhop.declare_operators(construct_operator(recipe))

def has_been_created(state, ID, name):
	if getattr(state, 'made_' + name)[ID] == True:
		return True
	else:
		setattr(state, 'made_' + name, {ID: True})
	return False

def is_tool_item(name, data):
	return name in data['Tools']

def is_operator(task):
	return task[0][:2] == 'op'

def extract_tasks(tasks, data):
	relevant_tasks = []
	for i in range(len(tasks)):
		if is_operator(tasks[i]) and tasks[i + 1][0] == 'have_enough':
			op_name = tasks[i][0].split('_')[-1]
			_, _, next_name, _ = tasks[i + 1]
			if op_name == next_name and not is_tool_item(op_name, data):
				relevant_tasks.append(op_name)
	return relevant_tasks

def detect_cycle(curr_task, tasks, data):
	if curr_task[0] != 'have_enough':
		return False
	items = extract_tasks(tasks[1:], data)
	_, _, current_item, _ = curr_task
	return current_item in items

def add_heuristic(data, ID):
	def heuristic(state, curr_task, tasks, plan, depth, calling_stack):
		if detect_cycle(curr_task, tasks, data):
			return True
		if depth > 100:
			return True

		if curr_task[0] == 'produce':
			ID = curr_task[1]
			name = curr_task[2]
			if is_tool_item(name, data) and has_been_created(state, ID, name):
				return True
		return False

	pyhop.add_check(heuristic)

def initialize_state(data, ID, time=0):
	state = pyhop.State('state')
	state.time = {ID: time}

	for item in data['Items']:
		setattr(state, item, {ID: 0})

	for item in data['Tools']:
		setattr(state, item, {ID: 0})

	for item, num in data['Initial'].items():
		setattr(state, item, {ID: num})

	state.made_bench = {ID: False}
	state.made_furnace = {ID: False}
	state.made_iron_axe = {ID: False}
	state.made_iron_pickaxe = {ID: False}
	state.made_stone_axe = {ID: False}
	state.made_stone_pickaxe = {ID: False}
	state.made_wooden_axe = {ID: False}
	state.made_wooden_pickaxe = {ID: False}
	return state

def initialize_goals(data, ID):
	goals = []
	for item, num in data['Goal'].items():
		goals.append(('have_enough', ID, item, num))
	return goals

if __name__ == '__main__':
	rules_filename = 'crafting.json'

	with open(rules_filename) as f:
		data = json.load(f)

	state = initialize_state(data, 'agent', time=239)
	goals = initialize_goals(data, 'agent')

	declare_operators(data)
	declare_methods(data)
	add_heuristic(data, 'agent')

	# pyhop.print_operators()
	# pyhop.print_methods()

	pyhop.pyhop(state, goals, verbose=3)

#-------------------------------------------------------------------------------
# Test cases for 6 scenarios with dynamic state setup
#-------------------------------------------------------------------------------

# Test Case 1
print("Test Case 1: Given {'plank': 1} achieve {'plank': 1} [time <= 0]")
with open(rules_filename) as f:
	data = json.load(f)
data['Initial'] = {'plank': 1}
data['Goal'] = {'plank': 1}
state = initialize_state(data, 'agent', time=0)
goals = initialize_goals(data, 'agent')
pyhop.pyhop(state, goals, verbose=3)

# Test Case 2
print("Test Case 2: Given {} achieve {'plank': 1} [time <= 300]")
with open(rules_filename) as f:
	data = json.load(f)
data['Initial'] = {}
data['Goal'] = {'plank': 1}
state = initialize_state(data, 'agent', time=300)
goals = initialize_goals(data, 'agent')
pyhop.pyhop(state, goals, verbose=3)

# Test Case 3
print("Test Case 3: Given {'plank': 3, 'stick': 2} achieve {'wooden_pickaxe': 1} [time <= 10]")
with open(rules_filename) as f:
	data = json.load(f)
data['Initial'] = {'plank': 3, 'stick': 2}
data['Goal'] = {'wooden_pickaxe': 1}
state = initialize_state(data, 'agent', time=10)
goals = initialize_goals(data, 'agent')
pyhop.pyhop(state, goals, verbose=3)

# Test Case 4
# print("Test Case 4: Given {} achieve {'iron_pickaxe': 1} [time <= 100]")
# with open(rules_filename) as f:
# 	data = json.load(f)
# data['Initial'] = {}
# data['Goal'] = {'iron_pickaxe': 1}
# state = initialize_state(data, 'agent', time=100)
# goals = initialize_goals(data, 'agent')
# pyhop.pyhop(state, goals, verbose=3)

# Test Case 5
# print("Test Case 5: Given {} achieve {'cart': 1, 'rail': 10} [time <= 175]")
# with open(rules_filename) as f:
# 	data = json.load(f)
# data['Initial'] = {}
# data['Goal'] = {'cart': 1, 'rail': 10}
# state = initialize_state(data, 'agent', time=175)
# goals = initialize_goals(data, 'agent')
# pyhop.pyhop(state, goals, verbose=3)

# Test Case 6
# print("Test Case 6: Given {} achieve {'cart': 1, 'rail': 20} [time <= 250]")
# with open(rules_filename) as f:
# 	data = json.load(f)
# data['Initial'] = {}
# data['Goal'] = {'cart': 1, 'rail': 20}
# state = initialize_state(data, 'agent', time=250)
# goals = initialize_goals(data, 'agent')
# pyhop.pyhop(state, goals, verbose=3)
