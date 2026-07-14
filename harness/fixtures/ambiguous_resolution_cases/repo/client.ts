const method = Math.random() > 0.5 ? "get" : "post";
axios[method](buildRuntimeUrl());
