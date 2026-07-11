
def test_simple_math():
	"""Simple test to verify testing setup."""
	assert 1 + 1 == 2


if __name__ == "__main__":
	try:
		test_simple_math()
		print("test_simple_math: PASS")
	except AssertionError:
		print("test_simple_math: FAIL")
		raise
