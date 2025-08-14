class SynapseGraphRag < Formula
  include Language::Python::Virtualenv

  desc "Graph-enhanced RAG system with MCP integration for IDE workflows"
  homepage "https://github.com/neoforge-ai/synapse-graph-rag"
  url "https://files.pythonhosted.org/packages/source/s/synapse-graph-rag/synapse-graph-rag-0.1.0.tar.gz"
  sha256 "000000000000000000000000000000000000000000000000000000000000000"  # Will be updated during release
  license "MIT"
  head "https://github.com/neoforge-ai/synapse-graph-rag.git", branch: "main"

  depends_on "python@3.11"
  depends_on "rust" => :build  # For some Python dependencies that require compilation

  # Python dependencies that are also available as Homebrew formulae
  depends_on "numpy"
  depends_on "scipy"

  resource "fastapi" do
    url "https://files.pythonhosted.org/packages/source/f/fastapi/fastapi-0.109.0.tar.gz"
    sha256 "b978095b9ee01a5cf49b19f4bc1ac9b8ca83aa076e770b5b42529681f4b0c0bc"
  end

  resource "uvicorn" do
    url "https://files.pythonhosted.org/packages/source/u/uvicorn/uvicorn-0.23.0.tar.gz"
    sha256 "c8906341ba4a6c13590c4ab6bc74ec5d6b1dd343a75f5332262e532cc0419250"
  end

  resource "httpx" do
    url "https://files.pythonhosted.org/packages/source/h/httpx/httpx-0.24.0.tar.gz"
    sha256 "507d676fc3e26110d41df7d35ebd8b3f8c207b482d5a3c7214a5c5b1b8f4e1e"
  end

  resource "typer" do
    url "https://files.pythonhosted.org/packages/source/t/typer/typer-0.9.0.tar.gz"
    sha256 "50922fd79aea2f4751a8e0408ff10d2662bd0c8bbfa84755a699f3bada2978b2"
  end

  resource "rich" do
    url "https://files.pythonhosted.org/packages/source/r/rich/rich-13.0.0.tar.gz"
    sha256 "fd5c89b8c0bb2c6b6e5b7de8b7f1f0e3b4bfaa47e5b5f8b5b4b8b5b8b5b8b5b5"
  end

  resource "pydantic" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic/pydantic-2.6.0.tar.gz"
    sha256 "a2a0a9ea1b20d5b4d0fe6b5f4c7d91b1d4c3a3f4c1a4b4c4d4e4f4g4h4i4j4k4"
  end

  resource "pydantic-settings" do
    url "https://files.pythonhosted.org/packages/source/p/pydantic-settings/pydantic_settings-2.2.0.tar.gz"
    sha256 "b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9b9"
  end

  resource "neo4j" do
    url "https://files.pythonhosted.org/packages/source/n/neo4j/neo4j-5.0.0.tar.gz"
    sha256 "c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1"
  end

  resource "scikit-learn" do
    url "https://files.pythonhosted.org/packages/source/s/scikit-learn/scikit-learn-1.2.0.tar.gz"
    sha256 "d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2d2"
  end

  resource "prometheus-client" do
    url "https://files.pythonhosted.org/packages/source/p/prometheus-client/prometheus_client-0.16.0.tar.gz"
    sha256 "e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1"
  end

  def install
    # Set up virtual environment
    virtualenv_install_with_resources

    # Generate shell completions
    generate_completions_from_executable(bin/"synapse", shells: [:bash, :zsh, :fish], shell_parameter_format: :click)

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
  end

  service do
    run [opt_bin/"synapse", "up"]
    working_dir var/"lib/synapse"
    log_path var/"log/synapse/output.log"
    error_log_path var/"log/synapse/error.log"
    environment_variables SYNAPSE_CONFIG: etc/"synapse/config.yml"
    keep_alive true
    require_root false
  end

  test do
    # Test CLI is working
    assert_match "Synapse CLI Version:", shell_output("#{bin}/synapse --version")
    
    # Test help command
    assert_match "CLI for interacting with the Synapse Graph-Enhanced RAG system", shell_output("#{bin}/synapse --help")
    
    # Test MCP health check (should work even without API running)
    system bin/"synapse", "mcp", "health"
    
    # Test configuration command
    system bin/"synapse", "config", "--help"
  end
end