module.exports = {
  apps: [
    {
      name: "monad-deploy",
      script: "24deploy.py",
      interpreter: "python3",
      autorestart: true,
      watch: false, // or true if the main-file was edit
      max_memory_restart: "120M",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/deploy-error.log",
      out_file: "logs/deploy-out.log",
      merge_logs: true,
      max_size: "10M",
      rotate_logs: true,
      env: {
        PYTHON_ENV: "production" // if use js NODE_ENV
      }
    },
    {
      name: "monad-gm",
      script: "gmonad.py",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "120M",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/gm-error.log",
      out_file: "logs/gm-out.log",
      merge_logs: true,
      max_size: "10M",
      rotate_logs: true,
      env: {
        PYTHON_ENV: "production"
      }
    },
    {
      name: "monad-pump",
      script: "curvance.py",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "120M",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/pump-error.log",
      out_file: "logs/pump-out.log",
      merge_logs: true,
      max_size: "10M",
      rotate_logs: true,
      env: {
        PYTHON_ENV: "production"
      }
    },
    {
      name: "monad-uniswap",
      script: "uniswap.py",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "120M",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/uniswap-error.log",
      out_file: "logs/uniswap-out.log",
      merge_logs: true,
      max_size: "10M",
      rotate_logs: true,
      env: {
        PYTHON_ENV: "production"
      }
    },
    {
      name: "monad-voting",
      script: "voting.py",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "120M",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/voting-error.log",
      out_file: "logs/voting-out.log",
      merge_logs: true,
      max_size: "10M",
      rotate_logs: true,
      env: {
        PYTHON_ENV: "production"
      }
    },
    {
      name: "monad-wallet",
      script: "generate.py",
      interpreter: "python3",
      autorestart: true,
      watch: false,
      max_memory_restart: "120M",
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "logs/wallet-error.log",
      out_file: "logs/wallet-out.log",
      merge_logs: true,
      max_size: "10M",
      rotate_logs: true,
      env: {
        PYTHON_ENV: "production"
      }
    }
  ]
};