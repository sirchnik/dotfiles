vim.o.clipboard = 'unnamedplus'
vim.wo.number = true
vim.o.scrolloff = 10

local lazypath = vim.fn.stdpath("data") .. "/lazy/lazy.nvim"
if not vim.loop.fs_stat(lazypath) then
    vim.fn.system(
        {"git", "clone", "--filter=blob:none", "https://github.com/folke/lazy.nvim.git", "--branch=stable", -- latest stable release
         lazypath})
end
vim.opt.rtp:prepend(lazypath)

require("lazy").setup({
{
  "folke/tokyonight.nvim",
  lazy = false,
  priority = 1000,
  opts = {},
  config = function()
	      require("tokyonight").setup({
          transparent = true,
    })
  end
},
--{
--   "folke/flash.nvim",
--   event = "VeryLazy",
--   --@type Flash.Config
--   opts = {
--           mode = {
--       	    search = {
--       		    enabled = false
--       	    }
--           }
--   },
--   -- stylua: ignore
--   keys = {
--       {
--       "S",
--       mode = {"n", "o", "x"},
--       function()
--           require("flash").jump()
--       end,
--       desc = "Flash"
--       }
--   }
--},
{
    "nvim-treesitter/nvim-treesitter",
    build = ":TSUpdate",
    setup = {
        --matchup = {
         --   enable = true,
        --}
    }
},
{
    "kylechui/nvim-surround",
    event = "VeryLazy",
    config = function()
        require("nvim-surround").setup({
            -- Configuration here, or leave empty to use defaults
        })
    end
},
{
    "andymass/vim-matchup",
    event = "VeryLazy",
    config = function()
	vim.g.matchup_matchparen_enabled = 0
    end
},
--{
--	"gbprod/yanky.nvim",
--	opts = {
--		system_clipboard = {
--			sync_with_ring = false,
--		},
--	},
--	keys = {
--		{ mode = { "n", "x" }, "p", "<Plug>(YankyPutAfter)" },
--		{ mode = { "n", "x" }, "P", "<Plug>(YankyPutBefore)" },
--		{ mode = { "n", "x" }, "gp", "<Plug>(YankyGPutAfter)" },
--		{ mode = { "n", "x" }, "gP", "<Plug>(YankyGPutBefore)" },
--		{ mode = "n", "<c-n>", "<Plug>(YankyCycleForward)" },
--		{ mode = "n", "<c-p>", "<Plug>(YankyCycleBackward)" },
--	},
--},
{
  '4e554c4c/darkman.nvim',
  build = 'go build -o bin/darkman.nvim',
  dependencies = { "folke/tokyonight.nvim" },
  config = function()
    require 'darkman'.setup(
	{
	  change_background = true,
	  send_user_event = false,
	  colorscheme = { dark = "tokyonight", light = "tokyonight-day" }
	})
  end,
},
})


