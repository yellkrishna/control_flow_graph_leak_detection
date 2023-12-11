   define i32 @SOURCE() {
    ret i32 42
}

define i32 @SINK(i32 %val) {
    ; Some operations in the sink function
    ret i32 0
}

define i32 @main() {
    %res = call i32 @SOURCE()
    call i32 @SINK(i32 %ase)
    ret i32 0
}
