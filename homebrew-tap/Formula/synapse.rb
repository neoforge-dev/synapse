class Synapse < Formula
  include Language::Python::Virtualenv

  desc "Graph-enhanced RAG system with MCP integration for IDE workflows"
  homepage "https://github.com/neoforge-ai/synapse-graph-rag"
  url "https://github.com/neoforge-ai/synapse-graph-rag/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license "MIT"
  head "https://github.com/neoforge-ai/synapse-graph-rag.git", branch: "main"

  depends_on "python@3.12"
  depends_on "cmake" => :build  # For building mgclient
  depends_on "pkg-config" => :build

  def install
    # Build and install pymgclient first
    cd "pymgclient" do
      system "python3", "setup.py", "build"
      system "python3", "setup.py", "install", "--prefix=#{libexec}"
    end

    # Install main package using virtualenv
    virtualenv_install_with_resources

    # Generate shell completions 
    generate_completions_from_executable(bin/"synapse", "--help", shells: [:bash, :zsh, :fish])

    # Create necessary directories
    (etc/"synapse").mkpath
    (var/"log/synapse").mkpath
    (var/"lib/synapse").mkpath
  end

  def post_install
    # Create default configuration if it doesn't exist
    config_file = etc/"synapse/config.yml"
    unless config_file.exist?
      config_file.write <<~EOS
        # Synapse GraphRAG Configuration
        api:
          host: 0.0.0.0
          port: 8000
          log_level: INFO

        memgraph:
          uri: bolt://localhost:7687
          username: ""
          password: ""

        embedding:
          model_name: all-MiniLM-L6-v2

        mcp:
          host: 127.0.0.1
          port: 8765
      EOS
    end

    # Print helpful post-install message
    ohai "Synapse GraphRAG installed successfully!"
    puts "Next steps:"
    puts "  1. Run 'synapse --help' to see available commands"
    puts "  2. Run 'synapse init wizard' to set up your first knowledge base"
    puts "  3. Run 'synapse up' to start the full stack (requires Docker)"
    puts ""
    puts "For vector-only mode (no Docker):"
    puts "  SYNAPSE_DISABLE_GRAPH=true synapse ingest ~/Documents"
  end

  test do
    # Test CLI is working
    assert_match "Synapse CLI Version:", shell_output("#{bin}/synapse --version")

    # Test help command
    assert_match "CLI for interacting with the Synapse Graph-Enhanced RAG system",
                 shell_output("#{bin}/synapse --help")
  end
end
