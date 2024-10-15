(function_definition
  name: (identifier) @name.definition.function
  parameters: (parameters 
    ; this query took 2 hours to write ...
    ; not sure why this even wors tbh
    ; not parsing args + kwargs for some fcking rason ... but honestly
    ; not super important
    [
      (parameter
        name: (identifier)
        type: (type)?) @parameter.definition.function
      (dictionary_splat_pattern)
    ]
  )
)

(class_definition
 name: (identifier) @name.definition.class
 (block (_) @class.definition.end .)
)

(call
  function: [
      (identifier) @name.reference.call
      (attribute
        attribute: (identifier) @name.reference.call)
  ]) @reference.call