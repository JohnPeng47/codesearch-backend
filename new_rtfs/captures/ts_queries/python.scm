;; scopes
;;
[
;;(block) too many scopes with this enabled??
 (lambda)

 ;; defs in comprehensions are limited to the
 ;; comprehension itself
 (list_comprehension)
 (dictionary_comprehension)
 (set_comprehension)
 (generator_expression)

 ;; compound statements
 (with_statement)
 (for_statement)

(function_definition)
(class_definition)
 ] @local.scope



;; defs

;; all assignments are counted as defs
(assignment
  left: (identifier) @local.definition.variable)

;; assignment patterns
;; a, b = 1, 2
(pattern_list
  (identifier) @local.definition.variable)

;; walrus
(named_expression
  .
  (identifier) @local.definition.variable)

;; def a()
(function_definition
  (identifier) @local.definition.function)

;; def _(a, b, c):
(parameters
  (identifier) @local.definition.parameter)

;; def_(a: str)
(typed_parameter
  (identifier) @local.definition.parameter)

;; lambda a, b, c: 
(lambda_parameters
  (identifier) @local.definition.parameter)

;; default params
;;
;;    def foo(printer=val):
;;
;; `printer` is a def
;; `val` is ignored
(default_parameter
  .
  (identifier) @local.definition.parameter)

;; patterns
(list_splat_pattern
  (identifier) @local.definition.variable)
(dictionary_splat_pattern
  (identifier) @local.definition.variable)
(tuple_pattern
  (identifier) @local.definition.variable)

;; with a as b:
;;
;; `b` is a def
(as_pattern
  (as_pattern_target
    (identifier) @local.definition.variable))

;; thing() for x in xs
;;
;; `x` is a def
(for_in_clause
  .
  "for"
  .
  (identifier) @local.definition.variable)

;; for a in b:
;;
;; `a` is a def
(for_statement
  .
  "for"
  .
  (identifier) @local.definition.variable)

;;Imports:

;;   
;;    import a, b
;;    import module.submodule.c
;;   
(import_statement
  (dotted_name
    (identifier) @local.import.name)+) @local.import.statement

;; Capture regular and relative imports
(import_from_statement
  module_name: 
    [
      (dotted_name) @local.import.module
      (relative_import
        (import_prefix) @local.import.prefix
        (dotted_name)? @local.import.module)
    ]
  name: 
    [
      ;; Single name or multiple names
      (dotted_name) @local.import.name
      ;; Capture all parts of dotted names
      (dotted_name 
        (identifier) @local.import.name.part)+
      ;; Capture individual identifiers in a tuple of names
      (aliased_import
        .
        (identifier) @local.import.name
        ("," (identifier) @local.import.name)*)
    ]
) @local.import.statement


;; TODO: add support for aliases


;; class A
(class_definition
  (identifier) @local.definition.class)

;; global a, b
(global_statement
  (identifier) @local.definition.variable)


;; refs

;;[a, b, c]
(list
  (identifier) @local.reference)

;; f-strings
(interpolation
  (identifier) @local.reference)

;; [ *a ]
(list_splat
  (identifier) @local.reference)

;; {a: A}
;; a is ignored
;; A is a ref
(dictionary
  (pair
    (identifier)
    (identifier) @local.reference))

;; **dict
(dictionary_splat
  (identifier) @local.reference)

;; {a, b, c}
(set
  (identifier) @local.reference)

;; a.b
;; `a` is a ref
;; `b` is ignored
(attribute
  .
  (identifier) @local.reference)

;; if we have self.field(), we can resolve field
;; safely
(attribute 
  (identifier) @_self_ident
  (identifier) @local.reference
  (#eq? @_self_ident "self"))

;; a[b]
(subscript
  (identifier) @local.reference)

;; a[i:j]
(slice
  (identifier) @local.reference)

;; a()
(call
  (identifier) @local.reference)

;; call arguments
(argument_list
  (identifier) @local.reference)

;; call(keyword=arg)
;; `keyword` is ignored
;; `arg` is a ref
(keyword_argument
  (_)
  (identifier) @local.reference)

;; TODO: capture call types
;; NOTE: currently ignoring keyword param name
;; call capture
(call
  function: (identifier) @local.call.name
  arguments: (argument_list
    (identifier)+ @local.call.arg.parameter
    (keyword_argument
      name: (_)?
      value: (identifier) @local.call.kwarg.parameter)+
  )?)

;; (a, b, c)
(tuple 
  (identifier) @local.reference)

;; for t in item
;;
;; `item` is a reference
(for_in_clause
  "in"
  (identifier) @local.reference)

;; for a in b:
;;
;; `b` is a ref
(for_statement
  "in"
  .
  (identifier) @local.reference)

;; with a as b:
;;
;; `a` is a ref
(as_pattern
  (identifier) @local.reference)

;; (a for a in ..)
(generator_expression
  (identifier) @local.reference)

;; await x
(await
  (identifier) @local.reference)

;; return x
(return_statement
  (identifier) @local.reference)

;; a + b
(binary_operator
  (identifier) @local.reference)

;; ~a
(unary_operator
  (identifier) @local.reference)

;; a and b
(boolean_operator
  (identifier) @local.reference)

;; not a 
(not_operator
  (identifier) @local.reference)

;; a in b
;; a < b
(comparison_operator
  (identifier) @local.reference)

;; a += 1
(augmented_assignment
  (identifier) @local.reference)

;; (a)
(parenthesized_expression
  (identifier) @local.reference)

;; a, b, c
(expression_list
  (identifier) @local.reference)

;; a;
(expression_statement
  (identifier) @local.reference)

;; z if x else y
(conditional_expression
  (identifier) @local.reference)

;; comprehensions
(list_comprehension
  (identifier) @local.reference)
(dictionary_comprehension
  (pair 
    (identifier) @local.reference))
(set_comprehension
  (identifier) @local.reference)

;; decorators
(decorator
  (identifier) @local.reference)

;; type refs
;;
;; def foo(a: T)
(parameters
  (typed_parameter
    (type
      (identifier) @local.reference)))

;; def foo() -> T:
(function_definition 
  return_type: 
  (type
    (identifier) @local.reference))

;; var: T = init()
(assignment 
  type:
  (type 
    (identifier) @local.reference))

;; python 2
;;
;; print item
(print_statement
  (identifier) @local.reference)
;; print >> a
(chevron
  (identifier) @local.reference)
;; assert a, b, c
(assert_statement
  (identifier) @local.reference)
;; exec '1+1'
(exec_statement
  (identifier) @local.reference)

;; del a, b, c
(delete_statement
  (identifier) @local.reference)

(while_statement
  (identifier) @local.reference)

(if_statement
  (identifier) @local.reference)

;; raise error from e 
(raise_statement
  (identifier) @local.reference)
